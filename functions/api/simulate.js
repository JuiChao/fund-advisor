// GET /api/simulate?code=160213&years=20&budget=2000
// 单基金模拟：优先从预计算数据查找，找不到则独立模拟
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const code = url.searchParams.get('code');
  const years = Math.max(5, Math.min(30, parseInt(url.searchParams.get('years')) || 20));
  const budget = Math.max(100, parseInt(url.searchParams.get('budget')) || 2000);
  const scale = budget / 1000;

  if (!code) {
    return new Response(JSON.stringify({ error: 'code parameter required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const fundsUrl = new URL('/data/funds.json', context.request.url).toString();
    const fundsResp = await context.env.ASSETS.fetch(fundsUrl);
    const funds = await fundsResp.json();
    const fund = funds.find(f => f.code === code);

    if (!fund) {
      return new Response(JSON.stringify({ error: 'Fund not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // 尝试从预计算数据中查找
    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const simsResp = await context.env.ASSETS.fetch(simsUrl);
    const sims = await simsResp.json();
    const yearKey = String(years);

    let matchingStrategy = null;
    let matchingVariant = null;
    for (const s of sims.strategies) {
      for (const vk of ['ideal', 'practical']) {
        const allocs = s[vk]?.allocations || [];
        if (allocs.some(a => a.code === code)) {
          matchingStrategy = s;
          matchingVariant = vk;
          break;
        }
      }
      if (matchingStrategy) break;
    }

    let simulation = null;

    if (matchingStrategy) {
      // 从预计算数据中获取
      const variant = matchingStrategy[matchingVariant];
      const yearData = variant?.by_years?.[yearKey];
      if (yearData) {
        const alloc = variant.allocations.find(a => a.code === code);
        const weight = alloc?.actual_weight || alloc?.weight || 1;
        simulation = {
          totalInvested: Math.round(yearData.totalInvested * scale * weight),
          medianFinal: Math.round((yearData.median || yearData.medianFinal) * scale * weight),
          p5: Math.round(yearData.p5 * scale * weight),
          p25: Math.round(yearData.p25 * scale * weight),
          p75: Math.round(yearData.p75 * scale * weight),
          p95: Math.round(yearData.p95 * scale * weight),
          annualReturn: yearData.annualReturn,
          meanReturnPct: yearData.meanReturnPct,
        };
      }
    }

    // 预计算数据中找不到，使用基金参数独立模拟
    if (!simulation) {
      simulation = simulateSingleFund(fund, years, budget);
    }

    return new Response(JSON.stringify({
      fund: { code: fund.code, name: fund.name, index_type: fund.index_type },
      params: { years, budget },
      simulation,
      note: matchingStrategy ? '基于预计算策略数据的近似结果' : '基于基金参数的独立模拟',
    }), {
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

// 基于基金参数的蒙特卡洛模拟
function simulateSingleFund(fund, years, budget) {
  const N_SIMS = 5000;
  const n_months = years * 12;
  const total_invested = budget * n_months;

  // 模拟参数
  const params = {
    nasdaq_return: 0.14, nasdaq_vol: 0.22,
    sp500_return: 0.11, sp500_vol: 0.18,
    fx_drift: 0.005, fx_vol: 0.03,
    dividend_yield: 0.008, dividend_tax: 0.10,
  };

  const is_sp = fund.index_type === '标普500';
  const te = fund.tracking_error || 0.015;
  const purchase_fee = fund.purchase_fee || 0.0012;
  const annual_fee = (fund.mgmt_fee || 0.008) + (fund.custody_fee || 0.002);

  const idx_ret_mean = (is_sp ? params.sp500_return : params.nasdaq_return) / 12;
  const idx_ret_vol = (is_sp ? params.sp500_vol : params.nasdaq_vol) / Math.sqrt(12);
  const te_vol = te / Math.sqrt(12);
  const fx_mean = params.fx_drift / 12;
  const fx_vol = params.fx_vol / Math.sqrt(12);
  const fee_m = annual_fee / 12;
  const div_m = params.dividend_yield / 12 * (1 - params.dividend_tax);
  const invest_per_month = budget * (1 - purchase_fee);

  // 简化的蒙特卡洛模拟（使用确定性随机种子）
  const final_values = [];
  const seed = hashStr(fund.code);

  for (let sim = 0; sim < N_SIMS; sim++) {
    let total_shares = 0;
    let nav = 1;
    const rng = createRNG(seed + sim);

    for (let m = 0; m < n_months; m++) {
      const idx_r = rng_normal(rng, idx_ret_mean, idx_ret_vol);
      const te_r = rng_normal(rng, 0, te_vol);
      const fx_r = rng_normal(rng, fx_mean, fx_vol);
      const fund_r = idx_r + te_r - fee_m + div_m + fx_r;
      nav *= (1 + fund_r);
      total_shares += invest_per_month / nav;
    }
    final_values.push(total_shares * nav);
  }

  final_values.sort((a, b) => a - b);

  const mean = final_values.reduce((s, v) => s + v, 0) / N_SIMS;
  const median = final_values[Math.floor(N_SIMS * 0.5)];
  const p5 = final_values[Math.floor(N_SIMS * 0.05)];
  const p25 = final_values[Math.floor(N_SIMS * 0.25)];
  const p75 = final_values[Math.floor(N_SIMS * 0.75)];
  const p95 = final_values[Math.floor(N_SIMS * 0.95)];

  const returns = (mean / total_invested - 1) * 100;

  return {
    totalInvested: total_invested,
    medianFinal: Math.round(median),
    p5: Math.round(p5),
    p25: Math.round(p25),
    p75: Math.round(p75),
    p95: Math.round(p95),
    annualReturn: round2(returns / years),
    meanReturnPct: round2(returns),
  };
}

function round2(v) { return Math.round(v * 100) / 100; }

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function createRNG(seed) {
  let s = seed || 1;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xFFFFFFFF;
    return (s >>> 0) / 0xFFFFFFFF;
  };
}

function rng_normal(rng, mean, std) {
  const u1 = rng();
  const u2 = rng();
  const z = Math.sqrt(-2 * Math.log(u1 || 1e-10)) * Math.cos(2 * Math.PI * u2);
  return mean + z * std;
}
