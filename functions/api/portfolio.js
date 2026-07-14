// GET /api/portfolio?years=20&budget=2000
// 返回3种策略 × 2种子方案（理论最优 + 实际可买）
// 动态应用额度分配算法，返回正确的、随实际预算调整后的配置比例
// 所有算法参数从 /data/algorithm.json 读取（单一数据源）
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const algoUrl = new URL('/data/algorithm.json', context.request.url).toString();
  const algoResp = await context.env.ASSETS.fetch(algoUrl);
  const CFG = await algoResp.json();

  const allocCfg = CFG.allocation;
  const scoringCfg = CFG.scoring;
  const defaults = CFG.defaults;
  const fundSel = CFG.fund_selection;
  const strategiesDef = CFG.strategies;

  const years = Math.max(allocCfg.years_min, Math.min(allocCfg.years_max, parseInt(url.searchParams.get('years')) || 20));
  const budget = Math.max(100, parseInt(url.searchParams.get('budget')) || 2000);
  const scale = budget / allocCfg.base_budget;
  const yearKey = String(years);

  try {
    // 1. 获取最新的基金数据和预计算模拟底表
    const fundsUrl = new URL('/data/funds.json', context.request.url).toString();
    const fundsResp = await context.env.ASSETS.fetch(fundsUrl);
    const funds = await fundsResp.json();

    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const simsResp = await context.env.ASSETS.fetch(simsUrl);
    const simsData = await simsResp.json();

    // 2. 动态额度分配算法和基金挑选逻辑（从共享配置读取参数）
    function scoreFund(f) {
      const fee = (f.mgmt_fee || 0) + (f.custody_fee || 0);
      const te = f.tracking_error || defaults.tracking_error_for_scoring;
      const scaleVal = f.scale || defaults.scale;
      const y3 = f.return_3yr;
      const ms = f.morningstar || defaults.morningstar;
      const pur = f.purchase_fee || defaults.purchase_fee;
      const s = scoringCfg;
      const feeS = Math.max(0, Math.min(100, 100 - (fee - s.fee.optimal) / s.fee.range * s.fee.penalty));
      const teS = Math.max(0, Math.min(100, 100 - (te - s.tracking_error.optimal) / s.tracking_error.range * s.tracking_error.penalty));
      const sc = s.scale;
      const scS = (scaleVal >= sc.optimal_min && scaleVal <= sc.optimal_max) ? sc.optimal_score
        : (scaleVal < sc.small_threshold ? sc.small_score
          : (scaleVal > sc.large_threshold ? sc.large_score : sc.mid_score));
      const y3S = y3 != null ? Math.max(0, Math.min(100, (y3 - s.return_3yr.baseline) / s.return_3yr.range * 100)) : s.return_3yr.null_default;
      const msS = ms > 0 ? ms * s.morningstar.multiplier : s.morningstar.null_default;
      const purS = Math.max(0, Math.min(100, 100 - (pur - s.purchase_fee.optimal) / s.purchase_fee.range * s.purchase_fee.penalty));
      const w = s.weights;
      return +(feeS * w.fee + teS * w.tracking_error + scS * w.scale + y3S * w.return_3yr + msS * w.morningstar + purS * w.purchase_fee).toFixed(1);
    }

    function rankFunds(list) {
      const scored = list.map(f => ({ ...f, score: scoreFund(f) }));
      scored.sort((a, b) => b.score - a.score);
      return scored.map((f, i) => ({ ...f, rank: i + 1 }));
    }

    function isBuyable(f) {
      const status = f.limit_status || '';
      return !status.includes('暂停');
    }

    function pickFundsByStyle(nqPct, onlyBuyable = false) {
      let nq = funds.filter(f => f.index_type === '纳斯达克100');
      let sp = funds.filter(f => f.index_type === '标普500');
      if (onlyBuyable) {
        nq = nq.filter(isBuyable);
        sp = sp.filter(isBuyable);
      }
      const rnq = rankFunds(nq).slice(0, fundSel.nasdaq_top_n);
      const rsp = rankFunds(sp).slice(0, fundSel.sp500_top_n);
      const items = [];
      const nqS = rnq.reduce((sum, f) => sum + f.score, 0);
      if (nqS > 0) {
        rnq.forEach(f => items.push({ fund: f, weight: (f.score / nqS) * nqPct }));
      }
      const spS = rsp.reduce((sum, f) => sum + f.score, 0);
      if (spS > 0) {
        rsp.forEach(f => items.push({ fund: f, weight: (f.score / spS) * (1 - nqPct) }));
      }
      return items;
    }

    function allocateIdeal(items) {
      const tradingDays = allocCfg.trading_days_per_month;
      const allocs = items.map(item => {
        const f = item.fund;
        const w = item.weight;
        const monthly = budget * w;
        const daily = monthly / tradingDays;
        return {
          code: f.code, name: f.name, index_type: f.index_type || '',
          weight: +w.toFixed(4), daily: +daily.toFixed(1), monthly: Math.round(monthly),
          fee: +((f.mgmt_fee || 0) + (f.custody_fee || 0)).toFixed(4),
          tracking_error: f.tracking_error, score: f.score || 0,
          daily_limit: f.daily_limit || null, limit_status: f.limit_status || '',
          exceeds_limit: false,
        };
      });
      const total = allocs.reduce((sum, a) => sum + a.monthly, 0);
      if (total > 0) {
        allocs.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
      }
      return allocs;
    }

    function allocatePractical(items) {
      const tradingDays = allocCfg.trading_days_per_month;
      const allocs = items.map(item => {
        const f = item.fund;
        const w = item.weight;
        const limit = f.daily_limit;
        const status = f.limit_status || '';
        const isSuspended = status.includes('暂停申购') || (status.includes('暂停') && limit === null);
        return {
          fund: f, weight: w, limit: (limit !== null && limit !== undefined) ? limit : Infinity,
          actual_daily: 0.0, actual_monthly: 0.0, exceeds_limit: false, is_suspended: isSuspended,
        };
      });

      let remainingBudget = budget;
      const activeAllocs = allocs.filter(a => !a.is_suspended);

      if (activeAllocs.length > 0) {
        while (remainingBudget > 0.01) {
          const available = activeAllocs.filter(a => !a.exceeds_limit);
          if (available.length === 0) break;

          let totalWeight = available.reduce((sum, a) => sum + a.weight, 0);
          if (totalWeight === 0) {
            available.forEach(a => a.weight = 1.0 / available.length);
            totalWeight = 1.0;
          }

          let allocatedInThisStep = false;
          for (const a of available) {
            const extraMonthly = remainingBudget * (a.weight / totalWeight);
            const targetMonthly = a.actual_monthly + extraMonthly;
            const targetDaily = targetMonthly / tradingDays;
            const limitMonthly = a.limit * tradingDays;

            if (targetDaily >= a.limit) {
              const added = limitMonthly - a.actual_monthly;
              a.actual_monthly = limitMonthly;
              a.actual_daily = a.limit;
              a.exceeds_limit = true;
              remainingBudget -= added;
              allocatedInThisStep = true;
            } else {
              a.actual_monthly = targetMonthly;
              a.actual_daily = targetDaily;
              remainingBudget -= extraMonthly;
              allocatedInThisStep = true;
            }
          }
          if (!allocatedInThisStep) break;
        }
      }

      const result = allocs.map(a => {
        const f = a.fund;
        return {
          code: f.code, name: f.name, index_type: f.index_type || '',
          weight: +a.weight.toFixed(4), daily: +a.actual_daily.toFixed(1), monthly: Math.round(a.actual_monthly),
          fee: +((f.mgmt_fee || 0) + (f.custody_fee || 0)).toFixed(4),
          tracking_error: f.tracking_error, score: f.score || 0,
          daily_limit: a.limit !== Infinity ? a.limit : null, limit_status: f.limit_status || '',
          exceeds_limit: a.exceeds_limit,
        };
      });

      const total = result.reduce((sum, a) => sum + a.monthly, 0);
      if (total > 0) {
        result.forEach(a => a.actual_weight = +(a.monthly / total).toFixed(4));
      }
      return result;
    }

    // 3. 构建结果并合并预计算的模拟收益
    const results = strategiesDef.map(sDef => {
      const idealItems = pickFundsByStyle(sDef.nq_pct, false);
      const practicalItems = pickFundsByStyle(sDef.nq_pct, true);

      const idealAllocations = allocateIdeal(idealItems);
      const practicalAllocations = allocatePractical(practicalItems);

      // 获取该策略在 simulations.json 中对应的预计算收益数据进行线性缩放
      const simStrategy = simsData.strategies.find(x => x.key === sDef.key);

      function scaleSimulation(variantKey) {
        const variantData = simStrategy?.[variantKey];
        const yearData = variantData?.by_years?.[yearKey];
        if (!yearData) return null;
        return {
          totalInvested: Math.round(yearData.totalInvested * scale),
          medianFinal: Math.round((yearData.median || 0) * scale),
          meanFinal: Math.round((yearData.mean || 0) * scale),
          p5: Math.round((yearData.p5 || 0) * scale),
          p25: Math.round((yearData.p25 || 0) * scale),
          p75: Math.round((yearData.p75 || 0) * scale),
          p95: Math.round((yearData.p95 || 0) * scale),
          annualReturn: yearData.annualReturn || 0,
          meanReturnPct: yearData.meanReturnPct || 0,
        };
      }

      return {
        key: sDef.key,
        name: sDef.name,
        description: sDef.description,
        icon: sDef.icon,
        nq_pct: sDef.nq_pct,
        ideal: {
          allocations: idealAllocations,
          note: '不考虑限购的理论最优配置。',
          simulation: scaleSimulation('ideal')
        },
        practical: {
          allocations: practicalAllocations,
          note: '排除暂停基金，遵守每日限购限额。',
          simulation: scaleSimulation('practical')
        }
      };
    });

    return new Response(JSON.stringify(results), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3600',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
