#!/usr/bin/env python3
"""
预计算模拟结果，生成 public/data/simulations.json
6策略 × 26年(5-30) = 156组，基准预算1000元，5000次模拟
"""
import json
import numpy as np
from pathlib import Path

FUNDS_PATH = Path('public/data/funds.json')
OUTPUT_PATH = Path('public/data/simulations.json')
BASE_BUDGET = 1000
N_SIMS = 5000
YEARS_RANGE = list(range(5, 31))

# 模拟参数
PARAMS = {
    'nasdaq_return': 0.14, 'nasdaq_vol': 0.22,
    'sp500_return': 0.11, 'sp500_vol': 0.18,
    'fx_drift': 0.005, 'fx_vol': 0.03,
    'dividend_yield': 0.008, 'dividend_tax': 0.10,
}

def load_funds():
    with open(FUNDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def score_fund(fund):
    fee = (fund.get('mgmt_fee') or 0) + (fund.get('custody_fee') or 0)
    te = fund.get('tracking_error') or 0.02
    scale = fund.get('scale') or 10
    y3 = fund.get('return_3yr')
    ms = fund.get('morningstar') or 0
    pur = fund.get('purchase_fee') or 0.0012

    fee_score = max(0, min(100, 100 - (fee - 0.004) / 0.006 * 50))
    te_score = max(0, min(100, 100 - (te - 0.008) / 0.022 * 67))
    scale_score = 100 if 10 <= scale <= 80 else (40 if scale < 5 else (70 if scale > 100 else 80))
    y3_score = max(0, min(100, (y3 - 0.3) / 0.6 * 100)) if y3 is not None else 50
    ms_score = ms * 25 if ms > 0 else 40
    pur_score = max(0, min(100, 100 - (pur - 0.0008) / 0.001 * 50))

    return round(fee_score * 0.35 + te_score * 0.25 + scale_score * 0.15 + y3_score * 0.12 + ms_score * 0.08 + pur_score * 0.05, 1)

def rank_funds(funds):
    scored = [{**f, 'score': score_fund(f)} for f in funds]
    scored.sort(key=lambda x: x['score'], reverse=True)
    for i, f in enumerate(scored):
        f['rank'] = i + 1
    return scored

def allocate(items, budget, apply_limits=True):
    trading_days = 22
    allocs = []
    for item in items:
        f = item['fund']
        w = item['weight']
        monthly = budget * w
        daily = monthly / trading_days
        limit = f.get('daily_limit') or 10
        if apply_limits and daily > limit:
            daily = limit
            monthly = daily * trading_days
        allocs.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'weight': round(w, 4), 'daily': round(daily, 1), 'monthly': round(monthly),
            'fee': round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0), 4),
            'tracking_error': f.get('tracking_error'), 'score': f.get('score', 0),
            'daily_limit': limit, 'limit_status': f.get('limit_status', ''),
            'exceeds_limit': apply_limits and (budget * w / trading_days) > limit,
        })
    total = sum(a['monthly'] for a in allocs)
    if total > 0:
        for a in allocs:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return allocs

# ---- 3种风格 × 2种子方案 ----

def pick_funds_by_style(funds, nq_pct):
    """按风格选取基金池：纳指nq_pct + 标普(1-nq_pct)"""
    nq = [f for f in funds if f.get('index_type') == '纳斯达克100']
    sp = [f for f in funds if f.get('index_type') == '标普500']
    rnq = rank_funds(nq)[:3]
    rsp = rank_funds(sp)[:2]
    items = []
    nq_s = sum(f['score'] for f in rnq)
    for f in rnq:
        items.append({'fund': f, 'weight': (f['score'] / nq_s) * nq_pct})
    sp_s = sum(f['score'] for f in rsp)
    for f in rsp:
        items.append({'fund': f, 'weight': (f['score'] / sp_s) * (1 - nq_pct)})
    return items

def build_strategy(key, name, desc, icon, nq_pct, funds, budget):
    """为一种风格生成理论最优+实际可买两个子方案"""
    items = pick_funds_by_style(funds, nq_pct)
    ideal = allocate(items, budget, apply_limits=False)
    practical = allocate(items, budget, apply_limits=True)

    # 检查实际可买是否有被截断的基金
    has_limited = any(a['exceeds_limit'] for a in practical)
    practical_note = '受限购影响，部分基金实际投入低于理论配置。' if has_limited else '当前限购不影响配置。'

    return {
        'key': key,
        'name': name,
        'description': desc,
        'icon': icon,
        'nq_pct': nq_pct,
        'ideal': {'allocations': ideal, 'note': '不考虑限购的理论最优配置。'},
        'practical': {'allocations': practical, 'note': practical_note},
    }

def generate_strategies(funds, budget=1000):
    return [
        build_strategy('growth', '进取型', '纳指70%+标普30%，追求高成长', '🚀', 0.7, funds, budget),
        build_strategy('balanced', '平衡型', '纳指50%+标普50%，攻守兼备', '⚖️', 0.5, funds, budget),
        build_strategy('conservative', '稳健型', '纳指30%+标普70%，注重稳定性', '🛡️', 0.3, funds, budget),
    ]

# ---- 蒙特卡洛模拟 ----

def simulate_portfolio(funds_list, weights, years, budget):
    """NumPy向量化蒙特卡洛模拟"""
    rng = np.random.default_rng(42)
    n_months = years * 12
    total_invested = budget * n_months
    final_values = np.zeros(N_SIMS)

    for fi, (fund, weight) in enumerate(zip(funds_list, weights)):
        fund_budget = budget * weight
        te = fund.get('tracking_error') or 0.015
        purchase_fee = fund.get('purchase_fee') or 0.0012
        annual_fee = (fund.get('mgmt_fee') or 0.008) + (fund.get('custody_fee') or 0.002)
        is_sp = fund.get('index_type') == '标普500'

        idx_ret_mean = (PARAMS['sp500_return'] if is_sp else PARAMS['nasdaq_return']) / 12
        idx_ret_vol = (PARAMS['sp500_vol'] if is_sp else PARAMS['nasdaq_vol']) / np.sqrt(12)
        te_vol = te / np.sqrt(12)
        fx_mean = PARAMS['fx_drift'] / 12
        fx_vol = PARAMS['fx_vol'] / np.sqrt(12)
        fee_m = annual_fee / 12
        div_m = PARAMS['dividend_yield'] / 12 * (1 - PARAMS['dividend_tax'])
        invest_per_month = fund_budget * (1 - purchase_fee)

        # 生成收益矩阵 (N_SIMS × n_months)
        idx_r = rng.normal(idx_ret_mean, idx_ret_vol, (N_SIMS, n_months))
        te_r = rng.normal(0, te_vol, (N_SIMS, n_months))
        fx_r = rng.normal(fx_mean, fx_vol, (N_SIMS, n_months))
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
                    sim = simulate_portfolio(sim_funds, sim_weights, y, BASE_BUDGET)
                    result[variant_key]['by_years'][str(y)] = sim
                    label = '理论' if variant_key == 'ideal' else '实际'
                    print(f'  {strat["name"]}/{label} / {y}年 → 中位终值 {sim["median"]:,}')

        strategies_result.append(result)

    output = {
        'generated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'base_budget': BASE_BUDGET,
        'n_simulations': N_SIMS,
        'years_range': YEARS_RANGE,
        'params': PARAMS,
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
