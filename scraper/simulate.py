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

def allocate(items, budget):
    trading_days = 22
    allocs = []
    for item in items:
        f = item['fund']
        w = item['weight']
        monthly = budget * w
        daily = monthly / trading_days
        limit = f.get('daily_limit') or 10
        if daily > limit:
            daily = limit
            monthly = daily * trading_days
        allocs.append({
            'code': f['code'], 'name': f['name'], 'index_type': f.get('index_type', ''),
            'weight': round(w, 4), 'daily': round(daily, 1), 'monthly': round(monthly),
            'fee': round((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0), 4),
            'tracking_error': f.get('tracking_error'), 'score': f.get('score', 0),
            'daily_limit': limit, 'limit_status': f.get('limit_status', ''),
        })
    total = sum(a['monthly'] for a in allocs)
    if total > 0:
        for a in allocs:
            a['actual_weight'] = round(a['monthly'] / total, 4)
    return allocs

# ---- 6种策略 ----

def strategy_unconstrained(funds):
    ranked = rank_funds(funds)
    low_fee = [f for f in ranked if ((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0)) < 0.007]
    rest = [f for f in ranked if f not in low_fee]
    items = []
    if low_fee:
        ts = sum(f['score'] for f in low_fee)
        for f in low_fee:
            items.append({'fund': f, 'weight': min((f['score'] / ts) * 0.6, 0.4)})
    if rest:
        top = rest[:5]
        ts = sum(f['score'] for f in top)
        for f in top:
            items.append({'fund': f, 'weight': min((f['score'] / ts) * 0.4, 0.3)})
    tw = sum(i['weight'] for i in items)
    for i in items:
        i['weight'] /= tw
    return {'key': 'unconstrained', 'name': '无约束最优', 'description': '不考虑限购，纯投资质量排序。低费率基金(<0.7%)优先分配60%。', 'items': items}

def strategy_available(funds):
    avail = [f for f in funds if '暂停' not in (f.get('limit_status') or '')]
    if not avail:
        return {'key': 'available', 'name': '实际可买', 'description': '无可用基金', 'items': []}
    ranked = rank_funds(avail)
    ts = sum(f['score'] for f in ranked)
    items = [{'fund': f, 'weight': f['score'] / ts} for f in ranked]
    return {'key': 'available', 'name': '实际可买', 'description': '剔除暂停申购基金后，按评分加权分配。', 'items': items}

def strategy_max_return(funds):
    ranked = rank_funds(funds)
    by_fee = sorted(ranked, key=lambda f: (f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0))
    top3 = by_fee[:3]
    ws = [0.5, 0.3, 0.2]
    items = [{'fund': f, 'weight': w} for f, w in zip(top3, ws)]
    return {'key': 'max_return', 'name': '最大收益', 'description': '集中配置费率最低的3只基金。风险相对集中。', 'items': items}

def strategy_balanced(funds, nq_pct=0.6):
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
    return {'key': 'balanced', 'name': '风险平衡', 'description': f'纳指{round(nq_pct*100)}%+标普{round((1-nq_pct)*100)}%，兼顾成长与稳健。', 'items': items}

def strategy_conservative(funds):
    s = strategy_balanced(funds, 0.4)
    s['key'] = 'conservative'
    s['name'] = '稳健保守'
    s['description'] = '纳指40%+标普60%，偏向低波动。'
    return s

def strategy_no_limit(funds):
    ranked = rank_funds(funds)
    low = [f for f in ranked if ((f.get('mgmt_fee') or 0) + (f.get('custody_fee') or 0)) < 0.008]
    pool = low if low else ranked[:3]
    ts = sum(f['score'] for f in pool)
    items = [{'fund': f, 'weight': f['score'] / ts} for f in pool]
    return {'key': 'no_limit_best', 'name': '最大收益(无限制)', 'description': '不考虑限购的理论最优，集中配置费率<0.8%的基金。', 'items': items}

ALL_STRATEGIES = [strategy_unconstrained, strategy_available, strategy_max_return, strategy_balanced, strategy_conservative, strategy_no_limit]

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
    strategies_result = []

    for strat_fn in ALL_STRATEGIES:
        strat = strat_fn(funds)
        items = strat['items']
        allocs = allocate(items, BASE_BUDGET)

        sim_funds = []
        sim_weights = []
        for a in allocs:
            f = next((x for x in funds if x['code'] == a['code']), None)
            if f:
                sim_funds.append(f)
                sim_weights.append(a.get('actual_weight', a.get('weight', 0)))

        by_years = {}
        if sim_funds:
            for y in YEARS_RANGE:
                sim = simulate_portfolio(sim_funds, sim_weights, y, BASE_BUDGET)
                by_years[str(y)] = sim
                print(f'  {strat["name"]} / {y}年 → 中位终值 {sim["median"]:,}')

        strategies_result.append({
            'key': strat['key'],
            'name': strat['name'],
            'description': strat['description'],
            'allocations': allocs,
            'by_years': by_years,
        })

    output = {
        'generated_at': __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
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
    print(f'\n输出: {OUTPUT_PATH} ({size_kb:.1f} KB)')
    print(f'策略数: {len(strategies_result)}')
    print(f'年份范围: {YEARS_RANGE[0]}-{YEARS_RANGE[-1]}')
    print(f'总模拟组数: {len(strategies_result) * len(YEARS_RANGE)}')

if __name__ == '__main__':
    main()
