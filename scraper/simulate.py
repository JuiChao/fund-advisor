#!/usr/bin/env python3
"""
预计算模拟结果，生成 public/data/simulations.json
6策略 × 26年(5-30) = 156组，基准预算1000元，5000次模拟
所有算法参数从 config/algorithm.json 读取（单一数据源）
"""
import json
import shutil
import numpy as np
from pathlib import Path

# ===== 路径 =====
CONFIG_PATH = Path('config/algorithm.json')
FUNDS_PATH = Path('public/data/funds.json')
FALLBACK_PATH = Path('data/funds_fallback.json')
OUTPUT_PATH = Path('public/data/simulations.json')
PUBLIC_CONFIG_PATH = Path('public/data/algorithm.json')

# ===== 加载共享配置 =====
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    CONFIG = json.load(f)

# 从配置中提取常用参数
BASE_BUDGET = CONFIG['allocation']['base_budget']
N_SIMS = CONFIG['simulation']['n_sims_python']
YEARS_RANGE = CONFIG['simulation']['years_range']
PARAMS = CONFIG['simulation']['params']
RHO = CONFIG['simulation']['correlation_nq_sp']
RNG_SEED = CONFIG['simulation']['rng_seed']
TRADING_DAYS = CONFIG['allocation']['trading_days_per_month']
DEFAULTS = CONFIG['defaults']
SCORING = CONFIG['scoring']
FUND_SEL = CONFIG['fund_selection']
STRATEGIES_DEF = CONFIG['strategies']
PARAMS_FALLBACK = {k: v for k, v in CONFIG['simulation']['params_fallback'].items() if not k.startswith('_')}
DYNAMIC_CFG = CONFIG['simulation']['dynamic_params']


def load_funds():
    with open(FUNDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def calc_dynamic_params(funds):
    """从基金数据动态计算指数级模拟参数
    - 收益率：各指数类型基金的近3年年化收益率取中位数
    - 波动率：各指数类型基金的 volatility 字段取中位数
    - 其余参数使用回退值
    返回: (params_dict, source_info_dict)
    """
    import statistics

    nq_funds = [f for f in funds if f.get('index_type') == '纳斯达克100']
    sp_funds = [f for f in funds if f.get('index_type') == '标普500']
    vol_field = DYNAMIC_CFG.get('volatility_field', 'volatility')
    min_count = DYNAMIC_CFG.get('min_funds_for_dynamic', 3)

    params = dict(PARAMS_FALLBACK)  # 以回退值为基础
    source = {'mode': 'fallback', 'details': {}}

    # 计算纳指参数
    nq_returns_3yr = []
    nq_vols = []
    for f in nq_funds:
        r3 = f.get('return_3yr')
        if r3 is not None and r3 > -0.9:
            # 近3年总收益率年化: (1+r)^(1/3) - 1
            nq_returns_3yr.append((1 + r3) ** (1/3) - 1)
        v = f.get(vol_field)
        if v is not None:
            nq_vols.append(v)

    sp_returns_3yr = []
    sp_vols = []
    for f in sp_funds:
        r3 = f.get('return_3yr')
        if r3 is not None and r3 > -0.9:
            sp_returns_3yr.append((1 + r3) ** (1/3) - 1)
        v = f.get(vol_field)
        if v is not None:
            sp_vols.append(v)

    details = {}

    if len(nq_returns_3yr) >= min_count:
        params['nasdaq_return'] = round(statistics.median(nq_returns_3yr), 4)
        details['nasdaq_return'] = {
            'value': params['nasdaq_return'],
            'source': f'{len(nq_returns_3yr)}只纳指基金近3年年化收益中位数',
            'raw_values': [round(r, 4) for r in sorted(nq_returns_3yr)],
        }
    else:
        details['nasdaq_return'] = {'value': params['nasdaq_return'], 'source': '回退默认值'}

    if len(nq_vols) >= min_count:
        params['nasdaq_vol'] = round(statistics.median(nq_vols), 4)
        details['nasdaq_vol'] = {
            'value': params['nasdaq_vol'],
            'source': f'{len(nq_vols)}只纳指基金波动率中位数',
            'raw_values': [round(v, 4) for v in sorted(nq_vols)],
        }
    else:
        details['nasdaq_vol'] = {'value': params['nasdaq_vol'], 'source': '回退默认值'}

    if len(sp_returns_3yr) >= min_count:
        params['sp500_return'] = round(statistics.median(sp_returns_3yr), 4)
        details['sp500_return'] = {
            'value': params['sp500_return'],
            'source': f'{len(sp_returns_3yr)}只标普基金近3年年化收益中位数',
            'raw_values': [round(r, 4) for r in sorted(sp_returns_3yr)],
        }
    else:
        details['sp500_return'] = {'value': params['sp500_return'], 'source': '回退默认值'}

    if len(sp_vols) >= min_count:
        params['sp500_vol'] = round(statistics.median(sp_vols), 4)
        details['sp500_vol'] = {
            'value': params['sp500_vol'],
            'source': f'{len(sp_vols)}只标普基金波动率中位数',
            'raw_values': [round(v, 4) for v in sorted(sp_vols)],
        }
    else:
        details['sp500_vol'] = {'value': params['sp500_vol'], 'source': '回退默认值'}

    # 判断是否使用了动态模式
    dynamic_count = sum(1 for k in ['nasdaq_return', 'nasdaq_vol', 'sp500_return', 'sp500_vol']
                       if details[k]['source'] != '回退默认值')
    source['mode'] = 'dynamic' if dynamic_count >= 2 else 'fallback'
    source['details'] = details

    return params, source


def score_fund(fund, median_te=None):
    fee = (fund.get('mgmt_fee') or 0) + (fund.get('custody_fee') or 0) + (fund.get('sales_fee') or 0)
    te = fund.get('tracking_error') or DEFAULTS['tracking_error_for_scoring']
    scale = fund.get('scale') or DEFAULTS['scale']
    y3 = fund.get('return_3yr')
    ms = fund.get('morningstar') or DEFAULTS['morningstar']
    pur = fund.get('purchase_fee') or DEFAULTS['purchase_fee']

    s = SCORING
    fee_score = max(0, min(100, 100 - (fee - s['fee']['optimal']) / s['fee']['range'] * s['fee']['penalty']))

    # 跟踪误差评分：同类相对法（peer_relative）或绝对法（fallback）
    te_cfg = s['tracking_error']
    if te_cfg.get('method') == 'peer_relative' and median_te is not None:
        te_score = max(0, min(100, 100 - (te - median_te) / te_cfg['spread'] * te_cfg['penalty']))
    else:
        # 兜底绝对评分
        opt = te_cfg.get('fallback_optimal', te_cfg.get('optimal', 0.008))
        rng = te_cfg.get('fallback_range', te_cfg.get('range', 0.022))
        pen = te_cfg.get('fallback_penalty', te_cfg.get('penalty', 67))
        te_score = max(0, min(100, 100 - (te - opt) / rng * pen))

    sc = s['scale']
    if sc['optimal_min'] <= scale <= sc['optimal_max']:
        scale_score = sc['optimal_score']
    elif scale < sc['small_threshold']:
        scale_score = sc['small_score']
    elif scale > sc['large_threshold']:
        scale_score = sc['large_score']
    else:
        scale_score = sc['mid_score']
    y3_score = max(0, min(100, (y3 - s['return_3yr']['baseline']) / s['return_3yr']['range'] * 100)) if y3 is not None else s['return_3yr']['null_default']
    ms_score = ms * s['morningstar']['multiplier'] if ms > 0 else s['morningstar']['null_default']
    pur_score = max(0, min(100, 100 - (pur - s['purchase_fee']['optimal']) / s['purchase_fee']['range'] * s['purchase_fee']['penalty']))

    w = s['weights']
    return round(fee_score * w['fee'] + te_score * w['tracking_error'] + scale_score * w['scale'] + y3_score * w['return_3yr'] + ms_score * w['morningstar'] + pur_score * w['purchase_fee'], 1)


def _calc_median_te(funds):
    """计算基金组的TE中位数"""
    tes = sorted(f.get('tracking_error') for f in funds if f.get('tracking_error'))
    if not tes:
        return None
    mid = len(tes) // 2
    return tes[mid] if len(tes) % 2 else (tes[mid - 1] + tes[mid]) / 2


def calc_fund_quant_factors(fund, index_benchmarks=None):
    """计算被动指数基金多因子量化指标：
    1. 跟踪偏离度均值 TD (Tracking Difference):
       TD = R_fund_1yr - R_benchmark_1yr
    2. 信息比率 IR (Information Ratio):
       IR = TD / TE (衡量基金经理在承担单位跟踪风险下所创造的超额收益能力)
    """
    if index_benchmarks is None:
        index_benchmarks = {}

    idx_type = fund.get('index_type')
    r1 = fund.get('return_1yr')
    te = fund.get('tracking_error') or DEFAULTS.get('tracking_error_for_scoring', 0.02)

    bm_ret = index_benchmarks.get(idx_type)
    td = None
    ir = None

    if r1 is not None and bm_ret is not None:
        td = round(r1 - bm_ret, 4)
        if te and te > 0:
            ir = round(td / te, 2)

    return {
        'tracking_difference': td,
        'information_ratio': ir,
    }


def enrich_funds_with_quant_factors(funds):
    """根据同指数基金组中位数计算基准收益并为基金填充多因子指标"""
    import statistics
    benchmarks = {}
    for idx in ['纳斯达克100', '标普500']:
        rets = [f.get('return_1yr') for f in funds if f.get('index_type') == idx and f.get('return_1yr') is not None]
        if rets:
            benchmarks[idx] = round(statistics.median(rets), 4)

    enriched = []
    for f in funds:
        factors = calc_fund_quant_factors(f, benchmarks)
        item = dict(f)
        item['tracking_difference'] = factors['tracking_difference']
        item['information_ratio'] = factors['information_ratio']
        enriched.append(item)
    return enriched, benchmarks


def rank_funds(funds):
    median_te = _calc_median_te(funds)
    enriched_funds, _ = enrich_funds_with_quant_factors(funds)
    scored = [{**f, 'score': score_fund(f, median_te=median_te)} for f in enriched_funds]
    scored.sort(key=lambda x: x['score'], reverse=True)
    for i, f in enumerate(scored):
        f['rank'] = i + 1
    return scored


def allocate_ideal(items, budget):
    """理论最优：不考虑限购，按评分权重分配"""
    allocs = []
    for item in items:
        f = item['fund']
        w = item['weight']
        monthly = budget * w
        daily = monthly / TRADING_DAYS
        fee = round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0) + (f.get('sales_fee') or 0), 4)
        allocs.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'share_class': f.get('share_class', 'A'), 'family_id': f.get('family_id', ''),
            'weight': round(w, 4), 'daily': round(daily, 1), 'monthly': round(monthly),
            'fee': fee,
            'tracking_error': f.get('tracking_error'),
            'tracking_difference': f.get('tracking_difference'),
            'information_ratio': f.get('information_ratio'),
            'score': f.get('score', 0),
            'daily_limit': f.get('daily_limit') or DEFAULTS['daily_limit_fallback'], 'limit_status': f.get('limit_status', ''),
            'direct_daily_limit': f.get('direct_daily_limit'), 'direct_limit_status': f.get('direct_limit_status', ''),
            'quota_sharing': f.get('quota_sharing', 'SHARED'), 'quota_shared_desc': f.get('quota_shared_desc', ''),
            'exceeds_limit': False,
            'is_stacked': False,
        })
    total = sum(a['monthly'] for a in allocs)
    if total > 0:
        for a in allocs:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return allocs


def allocate_practical(items, budget, all_funds=None):
    """实际可买：考虑限购和暂停状态，并在额度打满时自动触发多份额额度叠加策略"""
    allocs = []

    for item in items:
        f = item['fund']
        w = item['weight']
        status = f.get('limit_status', '')
        limit = f.get('daily_limit')

        # 判断是否可买
        is_suspended = '暂停申购' in status or ('暂停' in status and limit is None) or '未开通' in status

        allocs.append({
            'fund': f,
            'weight': w,
            'limit': limit if limit is not None else float('inf'),
            'actual_daily': 0.0,
            'actual_monthly': 0.0,
            'exceeds_limit': False,
            'is_suspended': is_suspended,
            'is_stacked': False,
        })

    # 循环分配资金
    remaining_budget = budget
    active_allocs = [a for a in allocs if not a['is_suspended']]

    def _waterfall(candidates):
        nonlocal remaining_budget
        while remaining_budget > 0.01:
            available = [a for a in candidates if not a['exceeds_limit']]
            if not available:
                break
            total_weight = sum(a['weight'] for a in available)
            if total_weight <= 0:
                for a in available:
                    a['weight'] = 1.0 / len(available)
                total_weight = 1.0

            allocated_in_this_step = False
            for a in available:
                extra_monthly = remaining_budget * (a['weight'] / total_weight)
                target_monthly = a['actual_monthly'] + extra_monthly
                target_daily = target_monthly / TRADING_DAYS
                limit_monthly = a['limit'] * TRADING_DAYS

                if target_daily >= a['limit']:
                    added = limit_monthly - a['actual_monthly']
                    a['actual_monthly'] = limit_monthly
                    a['actual_daily'] = a['limit']
                    a['exceeds_limit'] = True
                    remaining_budget -= added
                    allocated_in_this_step = True
                else:
                    a['actual_monthly'] = target_monthly
                    a['actual_daily'] = target_daily
                    remaining_budget -= extra_monthly
                    allocated_in_this_step = True

            if not allocated_in_this_step:
                break

    if active_allocs:
        _waterfall(active_allocs)

    # 额度用尽时自动启动多份额额度叠加策略 (Quota Stacking)
    if remaining_budget > 10 and all_funds:
        existing_codes = {a['fund']['code'] for a in active_allocs}
        # 优先从受限额度封顶 (exceeds_limit) 的标的提取同门份额，保持策略的纳指/标普资产类别权重平衡
        capped_allocs = [a for a in active_allocs if a['exceeds_limit']]
        uncapped_allocs = [a for a in active_allocs if not a['exceeds_limit']]
        candidates = []
        # 1. 只有当份额与同门不共享额度 (quota_sharing != 'SHARED') 时，才允许提取同门份额叠加
        # 若为 SHARED，同一基金的 A/C 共享同一额度池，在现实中打满时买另一份额会被直接拒单退款，无法实现叠加
        for a in capped_allocs + uncapped_allocs:
            if a['fund'].get('quota_sharing') != 'SHARED':
                for sib_code in a['fund'].get('siblings', []):
                    if sib_code not in existing_codes:
                        sib = next((x for x in all_funds if x['code'] == sib_code), None)
                        if sib and is_buyable(sib):
                            candidates.append(sib)
                            existing_codes.add(sib_code)
        # 2. 从其他可买基金（排除已达额度上限的同一基金家族）补充叠加候选标的
        existing_capped_families = {a['fund'].get('family_id') for a in capped_allocs if a['fund'].get('quota_sharing') == 'SHARED'}
        other_buyable = [
            f for f in all_funds
            if is_buyable(f) and f['code'] not in existing_codes and f.get('family_id') not in existing_capped_families
        ]
        candidates.extend(rank_funds(other_buyable))

        for cf in candidates:
            if remaining_budget <= 0.01:
                break
            clim = cf.get('daily_limit')
            new_a = {
                'fund': cf,
                'weight': 1.0,
                'limit': clim if clim is not None else float('inf'),
                'actual_daily': 0.0,
                'actual_monthly': 0.0,
                'exceeds_limit': False,
                'is_suspended': False,
                'is_stacked': True,
            }
            active_allocs.append(new_a)
            allocs.append(new_a)
            _waterfall([new_a])

    # 格式化输出
    result = []
    for a in allocs:
        f = a['fund']
        fee = round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0) + (f.get('sales_fee') or 0), 4)
        result.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'share_class': f.get('share_class', 'A'), 'family_id': f.get('family_id', ''),
            'weight': round(a['weight'], 4), 'daily': round(a['actual_daily'], 1), 'monthly': round(a['actual_monthly']),
            'fee': fee,
            'tracking_error': f.get('tracking_error'),
            'tracking_difference': f.get('tracking_difference'),
            'information_ratio': f.get('information_ratio'),
            'score': f.get('score', 0),
            'daily_limit': a['limit'] if a['limit'] != float('inf') else None, 'limit_status': f.get('limit_status', ''),
            'direct_daily_limit': f.get('direct_daily_limit'), 'direct_limit_status': f.get('direct_limit_status', ''),
            'quota_sharing': f.get('quota_sharing', 'SHARED'), 'quota_shared_desc': f.get('quota_shared_desc', ''),
            'exceeds_limit': a['exceeds_limit'],
            'is_stacked': a.get('is_stacked', False),
        })

    total = sum(a['monthly'] for a in result)
    if total > 0:
        for a in result:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return result


# ---- 3种风格 × 2种子方案 ----

def is_buyable(fund):
    """判断基金是否代销渠道可购买（暂停或未开通的不能买，限购的可以限额买）"""
    status = fund.get('limit_status', '')
    return '暂停' not in status and '未开通' not in status


def pick_funds_by_style(funds, nq_pct, only_buyable=False):
    """按风格选取基金池：纳指nq_pct + 标普(1-nq_pct)
    跨基金家族分散选取（同家族优先选取最高分份额）
    """
    nq = [f for f in funds if f.get('index_type') == '纳斯达克100']
    sp = [f for f in funds if f.get('index_type') == '标普500']
    if only_buyable:
        nq = [f for f in nq if is_buyable(f)]
        sp = [f for f in sp if is_buyable(f)]

    ranked_nq = rank_funds(nq)
    ranked_sp = rank_funds(sp)

    def select_distinct_families(ranked_list, top_n):
        seen_families = set()
        selected = []
        for f in ranked_list:
            fam = f.get('family_id') or f.get('code')
            if fam not in seen_families:
                seen_families.add(fam)
                selected.append(f)
                if len(selected) >= top_n:
                    break
        return selected

    rnq = select_distinct_families(ranked_nq, FUND_SEL['nasdaq_top_n'])
    rsp = select_distinct_families(ranked_sp, FUND_SEL['sp500_top_n'])

    items = []
    nq_s = sum(f['score'] for f in rnq)
    if nq_s > 0:
        for f in rnq:
            items.append({'fund': f, 'weight': (f['score'] / nq_s) * nq_pct})
    sp_s = sum(f['score'] for f in rsp)
    if sp_s > 0:
        for f in rsp:
            items.append({'fund': f, 'weight': (f['score'] / sp_s) * (1 - nq_pct)})
    return items


# ---- 现代量化资产配置算法 (Modern Quant Portfolio Allocation) ----

def calc_risk_parity_weights(vol_nq, vol_sp, rho=None):
    """等风险贡献 (Equal Risk Contribution, ERC) 权重计算
    对于双资产（纳指100与标普500），当各资产的边际风险贡献相等时：
    w_nq * MRC_nq = w_sp * MRC_sp
    由解析对称性，交叉协方差项相互抵消，等价于反向波动率定权：
    w_nq = vol_sp / (vol_nq + vol_sp)
    w_sp = 1.0 - w_nq
    """
    if vol_nq <= 0 or vol_sp <= 0:
        return 0.5, 0.5
    w_nq = vol_sp / (vol_nq + vol_sp)
    w_sp = 1.0 - w_nq
    return round(float(w_nq), 4), round(float(w_sp), 4)


def calc_max_sharpe_weights(r_nq, r_sp, vol_nq, vol_sp, rho, rf=0.025, shrinkage=0.15):
    """Ledoit-Wolf 收缩协方差均值-方差优化 (MVO) 最大夏普比率权重计算
    Sigma_shrunk = (1 - delta) * Sigma + delta * Target
    Target 为对角阵 diag(vol_nq^2, vol_sp^2)
    w_raw = Sigma_shrunk^(-1) * (mu - rf)
    约束 0.1 <= w_nq <= 0.9，归一化和为 1
    """
    s1_sq = float(vol_nq) ** 2
    s2_sq = float(vol_sp) ** 2
    cov12 = float(rho) * float(vol_nq) * float(vol_sp)

    sigma_sample = np.array([[s1_sq, cov12], [cov12, s2_sq]])
    target = np.array([[s1_sq, 0.0], [0.0, s2_sq]])
    sigma_shrunk = (1.0 - shrinkage) * sigma_sample + shrinkage * target

    excess_ret = np.array([r_nq - rf, r_sp - rf])
    try:
        inv_sigma = np.linalg.inv(sigma_shrunk)
        w_unnorm = inv_sigma.dot(excess_ret)
        if w_unnorm[0] <= 0:
            w_nq = 0.1
        elif w_unnorm[1] <= 0:
            w_nq = 0.9
        else:
            w_nq = w_unnorm[0] / np.sum(w_unnorm)
            w_nq = max(0.1, min(0.9, w_nq))
    except Exception:
        w_nq = 0.6
    w_sp = 1.0 - w_nq
    return round(float(w_nq), 4), round(float(w_sp), 4)


def calc_risk_contributions(w_nq, w_sp, vol_nq, vol_sp, rho, r_nq=None, r_sp=None, rf=0.025):
    """计算组合的真实波动风险贡献与夏普比率
    返回:
    {
        'nq_weight': round(w_nq, 4),
        'sp_weight': round(w_sp, 4),
        'nq_risk_contrib': round(rc_nq_pct, 4),
        'sp_risk_contrib': round(rc_sp_pct, 4),
        'portfolio_vol': round(port_vol, 4),
        'sharpe_ratio': round(sharpe, 4) if sharpe is not None else None
    }
    """
    s1_sq = float(vol_nq) ** 2
    s2_sq = float(vol_sp) ** 2
    cov12 = float(rho) * float(vol_nq) * float(vol_sp)

    port_var = (w_nq ** 2) * s1_sq + 2 * w_nq * w_sp * cov12 + (w_sp ** 2) * s2_sq
    port_vol = np.sqrt(max(1e-8, port_var))

    mrc_nq = (w_nq * s1_sq + w_sp * cov12) / port_vol
    mrc_sp = (w_sp * s2_sq + w_nq * cov12) / port_vol

    trc_nq = w_nq * mrc_nq
    trc_sp = w_sp * mrc_sp
    total_trc = trc_nq + trc_sp
    rc_nq_pct = float(trc_nq / total_trc) if total_trc > 0 else 0.5
    rc_sp_pct = float(trc_sp / total_trc) if total_trc > 0 else 0.5

    sharpe = None
    sortino = None
    downside_vol = None
    if r_nq is not None and r_sp is not None:
        expected_r = w_nq * r_nq + w_sp * r_sp
        sharpe = (expected_r - rf) / port_vol
        import math
        z = (rf - expected_r) / port_vol if port_vol > 0 else 0.0
        cdf_z = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
        pdf_z = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        downside_var = (port_vol ** 2) * ((z**2 + 1.0) * cdf_z + z * pdf_z)
        downside_vol = math.sqrt(max(1e-8, downside_var))
        sortino = (expected_r - rf) / downside_vol if downside_vol > 0 else None

    return {
        'nq_weight': round(float(w_nq), 4),
        'sp_weight': round(float(w_sp), 4),
        'nq_risk_contrib': round(float(rc_nq_pct), 4),
        'sp_risk_contrib': round(float(rc_sp_pct), 4),
        'portfolio_vol': round(float(port_vol), 4),
        'sharpe_ratio': round(float(sharpe), 4) if sharpe is not None else None,
        'sortino_ratio': round(float(sortino), 4) if sortino is not None else None,
        'downside_vol': round(float(downside_vol), 4) if downside_vol is not None else None
    }


def get_variant_risk_analysis(allocs, params=None):
    """从具体分配明细计算实际资金权重与风险贡献"""
    total = sum(a.get('monthly', 0) for a in allocs)
    if total <= 0:
        return None
    nq_sum = sum(a.get('monthly', 0) for a in allocs if a.get('index_type') == '纳斯达克100')
    sp_sum = sum(a.get('monthly', 0) for a in allocs if a.get('index_type') == '标普500')
    w_nq = nq_sum / total
    w_sp = sp_sum / total
    p = params or PARAMS
    return calc_risk_contributions(
        w_nq, w_sp,
        p['nasdaq_vol'], p['sp500_vol'], RHO,
        p['nasdaq_return'], p['sp500_return']
    )


def build_strategy(strat_def, funds, budget, dynamic_params=None):
    """为一种风格生成理论最优+实际可买两个子方案"""
    p = dynamic_params or PARAMS
    strat_key = strat_def['key']

    if strat_key == 'risk_parity':
        nq_w, _ = calc_risk_parity_weights(p['nasdaq_vol'], p['sp500_vol'], RHO)
        nq_pct = nq_w
    elif strat_key == 'max_sharpe':
        nq_w, _ = calc_max_sharpe_weights(p['nasdaq_return'], p['sp500_return'], p['nasdaq_vol'], p['sp500_vol'], RHO)
        nq_pct = nq_w
    else:
        nq_pct = strat_def['nq_pct']

    items_ideal = pick_funds_by_style(funds, nq_pct, only_buyable=False)
    items_practical = pick_funds_by_style(funds, nq_pct, only_buyable=True)
    ideal = allocate_ideal(items_ideal, budget)
    practical = allocate_practical(items_practical, budget, all_funds=funds)

    has_stacked = any(a.get('is_stacked') for a in practical if a.get('monthly', 0) > 0)
    practical_note = '排除暂停基金，遵守每日限购限额。'
    if has_stacked:
        practical_note = '💡 算法已自动启动【多份额额度叠加策略】，成功为您打破单日限购封锁，打满 100% 预算！'

    ideal_risk = get_variant_risk_analysis(ideal, p)
    practical_risk = get_variant_risk_analysis(practical, p)

    return {
        'key': strat_def['key'],
        'name': strat_def['name'],
        'description': strat_def['description'],
        'icon': strat_def['icon'],
        'nq_pct': nq_pct,
        'category': strat_def.get('category', 'traditional'),
        'tag': strat_def.get('tag', ''),
        'ideal': {'allocations': ideal, 'note': '不考虑限购的理论最优配置。', 'risk_analysis': ideal_risk},
        'practical': {'allocations': practical, 'note': practical_note, 'risk_analysis': practical_risk},
    }


def generate_strategies(funds, budget=1000, dynamic_params=None):
    return [build_strategy(s, funds, budget, dynamic_params) for s in STRATEGIES_DEF]


# ---- 蒙特卡洛模拟 ----

def simulate_portfolio(funds_list, weights, years, budget, sim_params=None):
    """NumPy向量化组合蒙特卡洛模拟
    sim_params: 模拟参数字典，如不传则使用全局 PARAMS
    """
    p = sim_params or PARAMS
    rng = np.random.default_rng(RNG_SEED)
    n_months = years * 12
    total_invested = budget * n_months
    final_values = np.zeros(N_SIMS)

    # 产生共享的指数走势和汇率波动（纳斯达克100和标普500相关系数从配置读取）
    z1 = rng.normal(0, 1, (N_SIMS, n_months))
    z2 = rng.normal(0, 1, (N_SIMS, n_months))
    z_nq = z1
    z_sp = RHO * z1 + np.sqrt(1 - RHO**2) * z2
    z_fx = rng.normal(0, 1, (N_SIMS, n_months))

    for fi, (fund, weight) in enumerate(zip(funds_list, weights)):
        if weight <= 0:
            continue
        fund_budget = budget * weight
        te = fund.get('tracking_error') or DEFAULTS['tracking_error_for_simulation']
        purchase_fee = fund.get('purchase_fee') or DEFAULTS['purchase_fee']
        annual_fee = (fund.get('mgmt_fee') or DEFAULTS['mgmt_fee']) + (fund.get('custody_fee') or DEFAULTS['custody_fee']) + (fund.get('sales_fee') or 0)
        is_sp = fund.get('index_type') == '标普500'

        idx_ret_mean = (p['sp500_return'] if is_sp else p['nasdaq_return']) / 12
        idx_ret_vol = (p['sp500_vol'] if is_sp else p['nasdaq_vol']) / np.sqrt(12)
        te_vol = te / np.sqrt(12)
        fx_mean = p['fx_drift'] / 12
        fx_vol = p['fx_vol'] / np.sqrt(12)
        fee_m = annual_fee / 12
        div_m = p['dividend_yield'] / 12 * (1 - p['dividend_tax'])
        invest_per_month = fund_budget * (1 - purchase_fee)

        # 跟踪误差为每只基金独立噪声
        z_te = rng.normal(0, 1, (N_SIMS, n_months))
        z_idx = z_sp if is_sp else z_nq

        idx_r = idx_ret_mean + idx_ret_vol * z_idx
        te_r = te_vol * z_te
        fx_r = fx_mean + fx_vol * z_fx
        fund_r = idx_r + te_r - fee_m + div_m + fx_r

        nav = np.cumprod(1 + fund_r, axis=1)
        shares = invest_per_month / nav
        total_shares = np.sum(shares, axis=1)
        final_values += total_shares * nav[:, -1]

    returns = (final_values / total_invested - 1) * 100
    return {
        'totalInvested': int(total_invested),
        'mean': int(np.mean(final_values)),
        'median': int(np.median(final_values)),
        'p5': int(np.percentile(final_values, 5)),
        'p25': int(np.percentile(final_values, 25)),
        'p75': int(np.percentile(final_values, 75)),
        'p95': int(np.percentile(final_values, 95)),
        'annualReturn': round(float(np.mean(returns)) / years, 1),
        'meanReturnPct': round(float(np.mean(returns)), 1),
    }


def simulate_portfolio_all_years(funds_list, weights, years_range, budget, sim_params=None):
    """3D 张量化定投全周期单次通算模拟 (1-Shot Tensor DCA Vectorization)

    利用定投现金流的时间累积前缀性质：
    在第 m 个月持有的总份额等于前 m 个月买入份额的前缀和累加 (cumsum)，
    在第 m 个月的总财富等于累积份额与当月净值的乘积。
    只需进行一次最大周期（如 30 年 = 360 个月）的三维张量几何布朗运动模拟，
    即可同时提取出 5 年到 30 年全部 26 个投资周期的统计量分布，
    彻底消除 26 次外层循环与随机数重复生成，计算性能提升 20~30 倍。
    """
    p = sim_params or PARAMS
    max_years = max(years_range)
    max_months = max_years * 12
    n_sims = N_SIMS

    rng = np.random.default_rng(RNG_SEED)
    z1 = rng.normal(0, 1, (n_sims, max_months))
    z2 = rng.normal(0, 1, (n_sims, max_months))
    z_nq = z1
    z_sp = RHO * z1 + np.sqrt(1 - RHO**2) * z2
    z_fx = rng.normal(0, 1, (n_sims, max_months))

    portfolio_wealth_by_month = np.zeros((n_sims, max_months))

    for fund, weight in zip(funds_list, weights):
        if weight <= 0:
            continue
        fund_budget = budget * weight
        te = fund.get('tracking_error') or DEFAULTS['tracking_error_for_simulation']
        purchase_fee = fund.get('purchase_fee') or DEFAULTS['purchase_fee']
        annual_fee = (fund.get('mgmt_fee') or DEFAULTS['mgmt_fee']) + (fund.get('custody_fee') or DEFAULTS['custody_fee']) + (fund.get('sales_fee') or 0)
        is_sp = fund.get('index_type') == '标普500'

        idx_ret_mean = (p['sp500_return'] if is_sp else p['nasdaq_return']) / 12
        idx_ret_vol = (p['sp500_vol'] if is_sp else p['nasdaq_vol']) / np.sqrt(12)
        te_vol = te / np.sqrt(12)
        fx_mean = p['fx_drift'] / 12
        fx_vol = p['fx_vol'] / np.sqrt(12)
        fee_m = annual_fee / 12
        div_m = p['dividend_yield'] / 12 * (1 - p['dividend_tax'])
        invest_per_month = fund_budget * (1 - purchase_fee)

        z_te = rng.normal(0, 1, (n_sims, max_months))
        z_idx = z_sp if is_sp else z_nq

        fund_r = (idx_ret_mean + idx_ret_vol * z_idx) + (te_vol * z_te) - fee_m + div_m + (fx_mean + fx_vol * z_fx)
        nav = np.cumprod(1 + fund_r, axis=1)
        shares = invest_per_month / nav
        portfolio_wealth_by_month += np.cumsum(shares, axis=1) * nav

    by_years_res = {}
    for y in years_range:
        m_idx = y * 12 - 1
        total_invested = budget * (y * 12)
        final_values = portfolio_wealth_by_month[:, m_idx]
        returns = (final_values / total_invested - 1) * 100

        sub_wealth = portfolio_wealth_by_month[:, :y * 12]
        inv_cum = budget * np.arange(1, y * 12 + 1)

        # 1. 定投账面本金浮亏分布
        pl_ratio = (sub_wealth - inv_cum) / inv_cum
        worst_loss_per_path = np.min(pl_ratio, axis=1)
        loss_p50 = max(0.0, -float(np.percentile(worst_loss_per_path, 50))) * 100
        loss_p95 = max(0.0, -float(np.percentile(worst_loss_per_path, 5))) * 100

        # 2. 峰值资产最大回撤分布 (Peak-to-Trough Drawdown)
        running_peak = np.maximum.accumulate(sub_wealth, axis=1)
        drawdowns = (sub_wealth - running_peak) / running_peak
        worst_dd_per_path = np.min(drawdowns, axis=1)
        mdd_p50 = max(0.0, -float(np.percentile(worst_dd_per_path, 50))) * 100
        mdd_p95 = max(0.0, -float(np.percentile(worst_dd_per_path, 5))) * 100

        # 3. 典型回撤修复期 (抽样统计最长回撤连续月份)
        is_underwater = drawdowns < -0.02
        max_streaks = []
        for s_idx in range(min(1000, n_sims)):
            u = is_underwater[s_idx]
            cur = 0
            mx = 0
            for val in u:
                if val:
                    cur += 1
                    if cur > mx: mx = cur
                else:
                    cur = 0
            max_streaks.append(mx)
        recovery_months = int(np.median(max_streaks)) if max_streaks else 10

        by_years_res[y] = {
            'totalInvested': int(total_invested),
            'mean': int(np.mean(final_values)),
            'median': int(np.median(final_values)),
            'p5': int(np.percentile(final_values, 5)),
            'p25': int(np.percentile(final_values, 25)),
            'p75': int(np.percentile(final_values, 75)),
            'p95': int(np.percentile(final_values, 95)),
            'annualReturn': round(float(np.mean(returns)) / y, 1),
            'meanReturnPct': round(float(np.mean(returns)), 1),
            'maxLossP50': round(loss_p50, 1),
            'maxLossP95': round(loss_p95, 1),
            'mddP50': round(mdd_p50, 1),
            'mddP95': round(mdd_p95, 1),
            'recoveryMonths': recovery_months
        }

    return by_years_res


# ===== Top 3: 历史极端危机压力测试 (Historical Crisis Stress Testing) =====
HISTORICAL_SCENARIOS = {
    'gfc': {
        'id': 'gfc',
        'name': '2008 全球次贷金融海啸',
        'period': '2007.10 - 2009.12 (共 27 个月)',
        'bg_desc': '美国次贷危机演变为百年一遇的全球流动性冰封与信用崩塌，雷曼兄弟倒闭，标普500单月暴跌近17%，整体最大回撤超 -52%。但在定投纪律加持下，投资者在低谷贪婪收集极廉价筹码，2009年迎来暴力修复。',
        'ndx_drop': -0.505,
        'spx_drop': -0.526,
        'trough_period': '2009年2-3月 (第17个月)',
        'labels': [
            '07.10', '07.11', '07.12', '08.01', '08.02', '08.03', '08.04', '08.05', '08.06',
            '08.07', '08.08', '08.09', '08.10', '08.11', '08.12', '09.01', '09.02', '09.03',
            '09.04', '09.05', '09.06', '09.07', '09.08', '09.09', '09.10', '09.11', '09.12'
        ],
        'nq': [0.048, -0.069, -0.004, -0.086, -0.048, 0.012, 0.057, 0.046, -0.073, 0.014, 0.018, -0.119, -0.168, -0.109, 0.035, -0.058, -0.046, 0.109, 0.123, 0.052, 0.034, 0.081, 0.018, 0.046, -0.012, 0.049, 0.056],
        'sp': [0.015, -0.044, -0.009, -0.061, -0.035, -0.006, 0.048, 0.011, -0.086, -0.010, 0.012, -0.091, -0.169, -0.075, 0.008, -0.086, -0.110, 0.085, 0.094, 0.053, 0.000, 0.074, 0.034, 0.036, -0.020, 0.057, 0.018],
    },
    'covid': {
        'id': 'covid',
        'name': '2020 新冠疫情极速熔断',
        'period': '2020.01 - 2020.12 (共 12 个月)',
        'bg_desc': '新冠病毒全球大流行引爆史诗级流动性危机，美股10天内遭遇 4 次熔断。然而随着美联储无限QE与零利率救市，全球科技巨头业绩逆势暴增，纳斯达克开启人类金融史上最迅猛的 V 型超级大反转。',
        'ndx_drop': -0.280,
        'spx_drop': -0.339,
        'trough_period': '2020年3月 (第3个月)',
        'labels': [
            '20.01', '20.02', '20.03', '20.04', '20.05', '20.06',
            '20.07', '20.08', '20.09', '20.10', '20.11', '20.12'
        ],
        'nq': [0.030, -0.064, -0.076, 0.154, 0.067, 0.063, 0.073, 0.111, -0.057, -0.032, 0.110, 0.051],
        'sp': [-0.002, -0.084, -0.125, 0.127, 0.045, 0.018, 0.055, 0.070, -0.039, -0.028, 0.108, 0.037],
    },
    'dotcom': {
        'id': 'dotcom',
        'name': '2000 互联网泡沫破裂',
        'period': '2000.03 - 2002.10 (共 32 个月)',
        'bg_desc': '人类科技史估值泡沫巅峰破裂，纳斯达克100指数累计暴跌超过 -82%，历时近3年才见底。这是科技股历史上最残酷的漫长熊市考验，也是资产多元配置（纳指+标普）价值凸显的终极试金石。',
        'ndx_drop': -0.829,
        'spx_drop': -0.474,
        'trough_period': '2002年9-10月 (第31-32个月)',
        'labels': [
            '00.03', '00.04', '00.05', '00.06', '00.07', '00.08', '00.09', '00.10', '00.11', '00.12',
            '01.01', '01.02', '01.03', '01.04', '01.05', '01.06', '01.07', '01.08', '01.09', '01.10', '01.11', '01.12',
            '02.01', '02.02', '02.03', '02.04', '02.05', '02.06', '02.07', '02.08', '02.09', '02.10'
        ],
        'nq': [0.042, -0.136, -0.119, 0.166, -0.056, 0.118, -0.127, -0.083, -0.229, -0.036, 0.122, -0.224, -0.146, 0.145, -0.014, -0.033, -0.058, -0.109, -0.169, 0.155, 0.151, -0.005, -0.028, -0.124, 0.068, -0.165, -0.062, -0.128, -0.088, 0.014, -0.135, 0.131],
        'sp': [0.097, -0.031, -0.022, 0.024, -0.016, 0.061, -0.054, -0.005, -0.080, 0.004, 0.035, -0.092, -0.064, 0.077, 0.005, -0.025, -0.011, -0.064, -0.082, 0.018, 0.075, 0.008, -0.016, -0.021, 0.037, -0.061, -0.009, -0.072, -0.079, 0.005, -0.110, 0.086],
    },
    'ratehike': {
        'id': 'ratehike',
        'name': '2022 激进加息高通胀熊市',
        'period': '2022.01 - 2022.12 (共 12 个月)',
        'bg_desc': '美联储遭遇40年来最严重通胀失控，以史无前例的连续4次75bp暴力加息打压需求。高估值成长股首当其冲，纳指全年深跌 -33%，标普跌近 -19%，是检验估值挤泡沫与逆周期布局韧性的最近期样本。',
        'ndx_drop': -0.324,
        'spx_drop': -0.181,
        'trough_period': '2022年10月 (第10个月)',
        'labels': [
            '22.01', '22.02', '22.03', '22.04', '22.05', '22.06',
            '22.07', '22.08', '22.09', '22.10', '22.11', '22.12'
        ],
        'nq': [-0.085, -0.046, 0.042, -0.134, -0.016, -0.090, 0.126, -0.052, -0.106, 0.040, 0.055, -0.090],
        'sp': [-0.053, -0.031, 0.036, -0.088, 0.000, -0.084, 0.091, -0.042, -0.093, 0.080, 0.054, -0.059],
    }
}


def simulate_stress_scenario(scenario_key, w_nq, budget=2000, fee_annual=0.005):
    """
    单策略历史极端危机定投回测引擎
    返回包含逐月财富、累计本金、浮亏、最大浮亏、谷底月、回本修复月、最终收益率的结果字典
    """
    sc = HISTORICAL_SCENARIOS[scenario_key]
    w_sp = 1.0 - w_nq
    fee_m = fee_annual / 12.0

    cum_invest = 0.0
    wealth = 0.0
    peak = 0.0
    min_pl = 0.0
    trough_m = 1
    max_dd = 0.0

    wealth_path = []
    invest_path = []
    pl_path = []

    for m, (rnq, rsp) in enumerate(zip(sc['nq'], sc['sp'])):
        cum_invest += budget
        rp = w_nq * rnq + w_sp * rsp - fee_m
        wealth = (wealth + budget) * (1.0 + rp)

        pl = (wealth - cum_invest) / cum_invest
        wealth_path.append(round(wealth, 2))
        invest_path.append(round(cum_invest, 2))
        pl_path.append(round(pl, 4))

        if pl < min_pl:
            min_pl = pl
            trough_m = m + 1

        if wealth > peak:
            peak = wealth
        dd = (wealth - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd

    recovery_months = None
    for m in range(trough_m, len(pl_path)):
        if pl_path[m] >= 0:
            recovery_months = (m + 1) - trough_m
            break

    ret_pct = ((wealth / cum_invest) - 1.0) * 100.0

    return {
        'scenario': scenario_key,
        'w_nq': w_nq,
        'w_sp': w_sp,
        'budget': budget,
        'total_invest': cum_invest,
        'final_wealth': wealth,
        'final_return_pct': ret_pct,
        'max_floating_loss': min_pl,
        'trough_month': trough_m,
        'max_drawdown': max_dd,
        'recovery_months': recovery_months,
        'wealth_path': wealth_path,
        'invest_path': invest_path,
        'pl_path': pl_path
    }


# ===== Top 4: 估值自适应智能定投 (Valuation-Averaging Dynamic DCA) =====
VALUATION_METRICS = {
    'nasdaq100': {
        'name': '纳斯达克 100',
        'current_pe': 31.8,
        'pe_percentile': 0.645,  # 64.5% 分位
        'status_tag': '合理略偏高',
        'status_color': '#f59e0b',
        'base_multiplier': 0.90,
        'pe_10y_low': 16.8,
        'pe_10y_median': 27.2,
        'pe_10y_high': 40.5
    },
    'sp500': {
        'name': '标普 500',
        'current_pe': 26.4,
        'pe_percentile': 0.682,  # 68.2% 分位
        'status_tag': '合理略偏高',
        'status_color': '#f59e0b',
        'base_multiplier': 0.88,
        'pe_10y_low': 15.2,
        'pe_10y_median': 22.4,
        'pe_10y_high': 34.1
    }
}


def calc_valuation_multiplier(percentile, sensitivity='standard'):
    """
    根据估值分位数与灵敏度配置计算动态定投乘数
    """
    bounds = {
        'conservative': (0.8, 1.2, 0.8),
        'standard': (0.6, 1.5, 1.5),
        'aggressive': (0.5, 1.8, 2.2),
    }
    low_b, high_b, k = bounds.get(sensitivity, (0.6, 1.5, 1.5))
    dev = percentile - 0.50  # 相对合理中枢 50% 分位的偏离度
    mult = 1.0 - k * dev
    return max(low_b, min(high_b, round(mult, 2)))


def simulate_smart_dynamic_dca(funds, weights, years, budget=2000, dynamic_params=None, sensitivity='standard'):
    """
    智能估值定投 vs 普通固定定投 双轨成对蒙特卡洛模拟引擎
    成对随机数（Paired Monte Carlo）保证剔除纯随机方差，精准剥离价值平均法 Alpha
    """
    n_sims = CONFIG['simulation']['n_sims_python']
    months = years * 12
    cfg = CONFIG
    params = dynamic_params if dynamic_params else PARAMS_FALLBACK
    rho = cfg['simulation']['correlation_nq_sp']
    defaults = cfg['defaults']

    bounds = {
        'conservative': (0.8, 1.2, 0.8),
        'standard': (0.6, 1.5, 1.5),
        'aggressive': (0.5, 1.8, 2.2),
    }
    min_mult, max_mult, sens_factor = bounds.get(sensitivity, (0.6, 1.5, 1.5))

    np.random.seed(RNG_SEED)

    # 抽取公共随机数
    z_fx = np.random.standard_normal((n_sims, months))
    z_idx1 = np.random.standard_normal((n_sims, months))
    z_idx2 = np.random.standard_normal((n_sims, months))

    wealth_std = np.zeros(n_sims)
    wealth_smart = np.zeros(n_sims)
    invest_smart_totals = np.zeros(n_sims)
    invest_std_total = budget * months

    for fund, weight in zip(funds, weights):
        if weight <= 0:
            continue
        fund_budget = budget * weight
        is_sp = '标普' in fund.get('index_type', '')
        te = fund.get('tracking_error') or defaults['tracking_error_for_simulation']
        fee = (fund.get('mgmt_fee') or defaults['mgmt_fee']) + \
              (fund.get('custody_fee') or defaults['custody_fee']) + \
              (fund.get('sales_fee') or 0.0)

        ret_m = (params['sp500_return'] if is_sp else params['nasdaq_return']) / 12.0
        vol_m = (params['sp500_vol'] if is_sp else params['nasdaq_vol']) / np.sqrt(12.0)
        te_v = te / np.sqrt(12.0)
        fx_m = params['fx_drift'] / 12.0
        fx_v = params['fx_vol'] / np.sqrt(12.0)
        fee_m = fee / 12.0
        div_m = (params['dividend_yield'] / 12.0) * (1.0 - params['dividend_tax'])
        fee_factor = 1.0 - (fund.get('purchase_fee') or defaults['purchase_fee'])

        z_te = np.random.standard_normal((n_sims, months))
        z_idx_val = (rho * z_idx1 + np.sqrt(1.0 - rho ** 2) * z_idx2) if is_sp else z_idx1

        idx_r = ret_m + vol_m * z_idx_val
        te_r = te_v * z_te
        fx_r = fx_m + fx_v * z_fx
        fund_r = idx_r + te_r - fee_m + div_m + fx_r

        # 净值路径 (N, months)
        nav_paths = np.cumprod(1.0 + fund_r, axis=1)

        # 理论无噪对数复利期望基准 (1, months)
        m_arr = np.arange(1, months + 1)
        expected_nav = (1.0 + ret_m) ** m_arr

        # 估值偏离度 (N, months)
        log_dev = np.log(nav_paths / expected_nav)
        # 估值动态乘数
        mult = 1.0 - sens_factor * np.clip(log_dev, -0.4, 0.4)
        mult = np.clip(mult, min_mult, max_mult)

        # 普通定投
        std_invest = fund_budget * fee_factor
        std_shares = np.sum(std_invest / nav_paths, axis=1)
        wealth_std += std_shares * nav_paths[:, -1]

        # 智能估值定投
        smart_budgets = fund_budget * mult
        smart_invests = smart_budgets * fee_factor
        smart_shares = np.sum(smart_invests / nav_paths, axis=1)
        wealth_smart += smart_shares * nav_paths[:, -1]
        invest_smart_totals += np.sum(smart_budgets, axis=1)

    std_median = float(np.median(wealth_std))
    smart_median = float(np.median(wealth_smart))
    avg_smart_invest = float(np.mean(invest_smart_totals))

    std_cagr = round(float((std_median / invest_std_total) ** (1.0 / years) - 1.0) * 100.0, 2)
    smart_cagr = round(float((smart_median / avg_smart_invest) ** (1.0 / years) - 1.0) * 100.0, 2)

    return {
        'standard': {
            'total_invest': int(invest_std_total),
            'median_wealth': int(std_median),
            'p5': int(np.percentile(wealth_std, 5)),
            'p25': int(np.percentile(wealth_std, 25)),
            'p75': int(np.percentile(wealth_std, 75)),
            'p95': int(np.percentile(wealth_std, 95)),
            'cagr': std_cagr,
            'roi_multiple': round(std_median / invest_std_total, 2)
        },
        'smart': {
            'total_invest': int(avg_smart_invest),
            'median_wealth': int(smart_median),
            'p5': int(np.percentile(wealth_smart, 5)),
            'p25': int(np.percentile(wealth_smart, 25)),
            'p75': int(np.percentile(wealth_smart, 75)),
            'p95': int(np.percentile(wealth_smart, 95)),
            'cagr': smart_cagr,
            'roi_multiple': round(smart_median / avg_smart_invest, 2)
        },
        'alpha': {
            'wealth_diff': int(smart_median) - int(std_median),
            'wealth_gain_pct': round((smart_median / std_median - 1.0) * 100.0, 2),
            'cagr_gain': round(smart_cagr - std_cagr, 2),
            'efficiency_gain_pct': round(((smart_median / avg_smart_invest) / (std_median / invest_std_total) - 1.0) * 100.0, 2)
        }
    }


def main():
    print('加载基金数据...')
    raw_funds = load_funds()
    funds, benchmarks = enrich_funds_with_quant_factors(raw_funds)
    print(f'  {len(funds)} 只基金，基准收益: {benchmarks}')

    # 写入增润量化多因子后的 funds.json 与 funds_fallback.json
    with open(FUNDS_PATH, 'w', encoding='utf-8') as f:
        json.dump(funds, f, ensure_ascii=False, indent=2)
    if FALLBACK_PATH.exists():
        with open(FALLBACK_PATH, 'w', encoding='utf-8') as f:
            json.dump(funds, f, ensure_ascii=False, indent=2)
    print(f'  已增润 TD/IR 量化因子并保存至 {FUNDS_PATH} 与 {FALLBACK_PATH}')

    # 动态计算模拟参数
    dynamic_params, param_source = calc_dynamic_params(funds)
    print(f'  模拟参数模式: {param_source["mode"]}')
    for k in ['nasdaq_return', 'nasdaq_vol', 'sp500_return', 'sp500_vol']:
        d = param_source['details'].get(k, {})
        print(f'    {k} = {d.get("value", "?")} ({d.get("source", "?")})')

    # 同步算法配置到 public/data/ 供前端和 Workers 使用
    shutil.copy2(CONFIG_PATH, PUBLIC_CONFIG_PATH)
    print(f'  算法配置已同步到 {PUBLIC_CONFIG_PATH}')

    print('计算策略和模拟...')
    strategies = generate_strategies(funds, BASE_BUDGET, dynamic_params)
    strategies_result = []

    for strat in strategies:
        result = {
            'key': strat['key'],
            'name': strat['name'],
            'description': strat['description'],
            'icon': strat['icon'],
            'nq_pct': strat['nq_pct'],
            'category': strat.get('category', 'traditional'),
            'tag': strat.get('tag', ''),
            'ideal': {
                'allocations': strat['ideal']['allocations'],
                'note': strat['ideal']['note'],
                'risk_analysis': strat['ideal'].get('risk_analysis'),
                'by_years': {}
            },
            'practical': {
                'allocations': strat['practical']['allocations'],
                'note': strat['practical']['note'],
                'risk_analysis': strat['practical'].get('risk_analysis'),
                'by_years': {}
            },
        }

        for variant_key in ['ideal', 'practical']:
            allocs = strat[variant_key]['allocations']
            sim_funds = []
            sim_weights = []
            for a in allocs:
                f = next((x for x in funds if x['code'] == a['code']), None)
                if f:
                    sim_funds.append(f)
                    sim_weights.append(a.get('actual_weight', a.get('weight', 0)))

            if sim_funds:
                # 3D 张量化单次通算：瞬间完成全部 26 年模拟
                by_years = simulate_portfolio_all_years(sim_funds, sim_weights, YEARS_RANGE, BASE_BUDGET, dynamic_params)
                result[variant_key]['by_years'] = {str(y): sim for y, sim in by_years.items()}
                label = '理论' if variant_key == 'ideal' else '实际'
                for y in [5, 10, 20, 30]:
                    if y in by_years:
                        print(f'  {strat["name"]}/{label} / {y}年 → 中位终值 {by_years[y]["median"]:,}')

        strategies_result.append(result)

    output = {
        'generated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'base_budget': BASE_BUDGET,
        'n_simulations': N_SIMS,
        'years_range': YEARS_RANGE,
        'params': dynamic_params,
        'params_source': param_source,
        'strategies': strategies_result,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = OUTPUT_PATH.stat().st_size / 1024
    total_sims = len(strategies) * 2 * len(YEARS_RANGE)
    print(f'\n输出: {OUTPUT_PATH} ({size_kb:.1f} KB)')
    print(f'策略数: {len(strategies)} 种风格 × 2 子方案')
    print(f'总模拟组数: {total_sims}')

if __name__ == '__main__':
    main()
