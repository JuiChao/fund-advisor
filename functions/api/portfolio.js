// GET /api/portfolio?years=20&budget=2000
// 返回3种策略 × 2种子方案（理论最优 + 实际可买）
// 动态应用额度分配算法，返回正确的、随实际预算调整后的配置比例
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const years = Math.max(5, Math.min(30, parseInt(url.searchParams.get('years')) || 20));
  const budget = Math.max(100, parseInt(url.searchParams.get('budget')) || 2000);
  const scale = budget / 1000;
  const yearKey = String(years);

  try {
    // 1. 获取最新的基金数据和预计算模拟底表
    const fundsUrl = new URL('/data/funds.json', context.request.url).toString();
    const fundsResp = await context.env.ASSETS.fetch(fundsUrl);
    const funds = await fundsResp.json();

    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const simsResp = await context.env.ASSETS.fetch(simsUrl);
    const simsData = await simsResp.json();

    // 2. 动态额度分配算法和基金挑选逻辑（与 Python 端完全对齐）
    function scoreFund(f) {
      const fee = (f.mgmt_fee || 0) + (f.custody_fee || 0);
      const te = f.tracking_error || 0.02;
      const scaleVal = f.scale || 10;
      const y3 = f.return_3yr;
      const ms = f.morningstar || 0;
      const pur = f.purchase_fee || 0.0012;
      const feeS = Math.max(0, Math.min(100, 100 - (fee - 0.004) / 0.006 * 50));
      const teS = Math.max(0, Math.min(100, 100 - (te - 0.008) / 0.022 * 67));
      const scS = (scaleVal >= 10 && scaleVal <= 80) ? 100 : (scaleVal < 5 ? 40 : (scaleVal > 100 ? 70 : 80));
      const y3S = y3 != null ? Math.max(0, Math.min(100, (y3 - 0.3) / 0.6 * 100)) : 50;
      const msS = ms > 0 ? ms * 25 : 40;
      const purS = Math.max(0, Math.min(100, 100 - (pur - 0.0008) / 0.001 * 50));
      return +(feeS * 0.35 + teS * 0.25 + scS * 0.15 + y3S * 0.12 + msS * 0.08 + purS * 0.05).toFixed(1);
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
      const rnq = rankFunds(nq).slice(0, 3);
      const rsp = rankFunds(sp).slice(0, 2);
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
      const tradingDays = 22;
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
      const tradingDays = 22;
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
    const results = simsData.strategies.map(s => {
      const idealItems = pickFundsByStyle(s.nq_pct, false);
      const practicalItems = pickFundsByStyle(s.nq_pct, true);

      const idealAllocations = allocateIdeal(idealItems);
      const practicalAllocations = allocatePractical(practicalItems);

      // 获取该策略在 simulations.json 中对应的预计算收益数据进行线性缩放
      const simStrategy = simsData.strategies.find(x => x.key === s.key);
      
      function scaleSimulation(variantKey) {
        const variantData = simStrategy?.[variantKey];
        const yearData = variantData?.by_years?.[yearKey];
        if (!yearData) return null;
        return {
          totalInvested: Math.round(yearData.totalInvested * scale),
          medianFinal: Math.round((yearData.median || yearData.medianFinal || 0) * scale),
          meanFinal: Math.round((yearData.mean || yearData.median || 0) * scale),
          p5: Math.round((yearData.p5 || 0) * scale),
          p25: Math.round((yearData.p25 || 0) * scale),
          p75: Math.round((yearData.p75 || 0) * scale),
          p95: Math.round((yearData.p95 || 0) * scale),
          annualReturn: yearData.annualReturn || 0,
          meanReturnPct: yearData.meanReturnPct || 0,
        };
      }

      return {
        key: s.key,
        name: s.name,
        description: s.description,
        icon: s.icon,
        nq_pct: s.nq_pct,
        ideal: {
          allocations: idealAllocations,
          note: s.ideal?.note || '不考虑限购的理论最优配置。',
          simulation: scaleSimulation('ideal')
        },
        practical: {
          allocations: practicalAllocations,
          note: s.practical?.note || '排除暂停基金，遵守每日限购限额。',
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
