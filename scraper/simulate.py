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


def score_fund(fund):
    fee = (fund.get('mgmt_fee') or 0) + (fund.get('custody_fee') or 0)
    te = fund.get('tracking_error') or DEFAULTS['tracking_error_for_scoring']
    scale = fund.get('scale') or DEFAULTS['scale']
    y3 = fund.get('return_3yr')
    ms = fund.get('morningstar') or DEFAULTS['morningstar']
    pur = fund.get('purchase_fee') or DEFAULTS['purchase_fee']

    s = SCORING
    fee_score = max(0, min(100, 100 - (fee - s['fee']['optimal']) / s['fee']['range'] * s['fee']['penalty']))
    te_score = max(0, min(100, 100 - (te - s['tracking_error']['optimal']) / s['tracking_error']['range'] * s['tracking_error']['penalty']))
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


def rank_funds(funds):
    scored = [{**f, 'score': score_fund(f)} for f in funds]
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
        allocs.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'weight': round(w, 4), 'daily': round(daily, 1), 'monthly': round(monthly),
            'fee': round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0), 4),
            'tracking_error': f.get('tracking_error'), 'score': f.get('score', 0),
            'daily_limit': f.get('daily_limit') or DEFAULTS['daily_limit_fallback'], 'limit_status': f.get('limit_status', ''),
            'exceeds_limit': False,
        })
    total = sum(a['monthly'] for a in allocs)
    if total > 0:
        for a in allocs:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return allocs


def allocate_practical(items, budget):
    """实际可买：考虑限购和暂停状态，优化实际可执行性（循环分配超额资金）"""
    allocs = []

    for item in items:
        f = item['fund']
        w = item['weight']
        status = f.get('limit_status', '')
        limit = f.get('daily_limit')

        # 判断是否可买
        is_suspended = '暂停申购' in status or ('暂停' in status and limit is None)

        allocs.append({
            'fund': f,
            'weight': w,
            'limit': limit if limit is not None else float('inf'),
            'actual_daily': 0.0,
            'actual_monthly': 0.0,
            'exceeds_limit': False,
            'is_suspended': is_suspended,
        })

    # 循环分配资金
    remaining_budget = budget
    active_allocs = [a for a in allocs if not a['is_suspended']]

    if active_allocs:
        while remaining_budget > 0.01:
            # 找到当前未达到上限的基金
            available = [a for a in active_allocs if not a['exceeds_limit']]
            if not available:
                break  # 所有可用基金都达到上限了，无法分配更多资金

            total_weight = sum(a['weight'] for a in available)
            if total_weight == 0:
                for a in available:
                    a['weight'] = 1.0 / len(available)
                total_weight = 1.0

            allocated_in_this_step = False
            for a in available:
                # 这一步应该分配给该基金的增量资金
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

    # 格式化输出
    result = []
    for a in allocs:
        f = a['fund']
        result.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'weight': round(a['weight'], 4), 'daily': round(a['actual_daily'], 1), 'monthly': round(a['actual_monthly']),
            'fee': round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0), 4),
            'tracking_error': f.get('tracking_error'), 'score': f.get('score', 0),
            'daily_limit': a['limit'] if a['limit'] != float('inf') else None, 'limit_status': f.get('limit_status', ''),
            'exceeds_limit': a['exceeds_limit'],
        })

    total = sum(a['monthly'] for a in result)
    if total > 0:
        for a in result:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return result


# ---- 3种风格 × 2种子方案 ----

def is_buyable(fund):
    """判断基金是否可购买（暂停的不能买，限购的可以限额买）"""
    status = fund.get('limit_status', '')
    return '暂停' not in status


def pick_funds_by_style(funds, nq_pct, only_buyable=False):
    """按风格选取基金池：纳指nq_pct + 标普(1-nq_pct)
    only_buyable=True时只选不限购的基金
    """
    nq = [f for f in funds if f.get('index_type') == '纳斯达克100']
    sp = [f for f in funds if f.get('index_type') == '标普500']
    if only_buyable:
        nq = [f for f in nq if is_buyable(f)]
        sp = [f for f in sp if is_buyable(f)]
    rnq = rank_funds(nq)[:FUND_SEL['nasdaq_top_n']]
    rsp = rank_funds(sp)[:FUND_SEL['sp500_top_n']]
    items = []
    nq_s = sum(f['score'] for f in rnq)
    for f in rnq:
        items.append({'fund': f, 'weight': (f['score'] / nq_s) * nq_pct})
    sp_s = sum(f['score'] for f in rsp)
    for f in rsp:
        items.append({'fund': f, 'weight': (f['score'] / sp_s) * (1 - nq_pct)})
    return items


def build_strategy(strat_def, funds, budget):
    """为一种风格生成理论最优+实际可买两个子方案"""
    nq_pct = strat_def['nq_pct']
    items_ideal = pick_funds_by_style(funds, nq_pct, only_buyable=False)
    items_practical = pick_funds_by_style(funds, nq_pct, only_buyable=True)
    ideal = allocate_ideal(items_ideal, budget)
    practical = allocate_practical(items_practical, budget)  # 排除暂停基金，遵守每日限额

    return {
        'key': strat_def['key'],
        'name': strat_def['name'],
        'description': strat_def['description'],
        'icon': strat_def['icon'],
        'nq_pct': nq_pct,
        'ideal': {'allocations': ideal, 'note': '不考虑限购的理论最优配置。'},
        'practical': {'allocations': practical, 'note': '排除暂停基金，遵守每日限购限额。'},
    }


def generate_strategies(funds, budget=1000):
    return [build_strategy(s, funds, budget) for s in STRATEGIES_DEF]


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
        annual_fee = (fund.get('mgmt_fee') or DEFAULTS['mgmt_fee']) + (fund.get('custody_fee') or DEFAULTS['custody_fee'])
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


def main():
    print('加载基金数据...')
    funds = load_funds()
    print(f'  {len(funds)} 只基金')

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
    strategies = generate_strategies(funds, BASE_BUDGET)
    strategies_result = []

    for strat in strategies:
        result = {
            'key': strat['key'],
            'name': strat['name'],
            'description': strat['description'],
            'icon': strat['icon'],
            'nq_pct': strat['nq_pct'],
            'ideal': {'allocations': strat['ideal']['allocations'], 'note': strat['ideal']['note'], 'by_years': {}},
            'practical': {'allocations': strat['practical']['allocations'], 'note': strat['practical']['note'], 'by_years': {}},
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
                for y in YEARS_RANGE:
                    sim = simulate_portfolio(sim_funds, sim_weights, y, BASE_BUDGET, dynamic_params)
                    result[variant_key]['by_years'][str(y)] = sim
                    label = '理论' if variant_key == 'ideal' else '实际'
                    print(f'  {strat["name"]}/{label} / {y}年 → 中位终值 {sim["median"]:,}')

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
