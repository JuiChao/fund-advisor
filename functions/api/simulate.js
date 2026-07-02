// GET /api/simulate?code=160213&years=20&budget=2000
// 单基金模拟结果（从预计算数据中查找最接近的策略）
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
    // 获取基金信息
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

    // 获取预计算数据中包含该基金的策略
    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const simsResp = await context.env.ASSETS.fetch(simsUrl);
    const sims = await simsResp.json();
    const yearKey = String(years);

    // 找到包含该基金的策略（检查 ideal 和 practical）
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
      const variant = matchingStrategy[matchingVariant];
      const yearData = variant?.by_years?.[yearKey];
      if (yearData) {
        // 找到该基金在策略中的权重
        const alloc = variant.allocations.find(a => a.code === code);
        const weight = alloc?.actual_weight || alloc?.weight || 1;

        simulation = {
          totalInvested: Math.round(yearData.totalInvested * scale * weight),
          medianFinal: Math.round(yearData.medianFinal * scale * weight),
          p5: Math.round(yearData.p5 * scale * weight),
          p25: Math.round(yearData.p25 * scale * weight),
          p75: Math.round(yearData.p75 * scale * weight),
          p95: Math.round(yearData.p95 * scale * weight),
          annualReturn: yearData.annualReturn,
          meanReturnPct: yearData.meanReturnPct,
        };
      }
    }

    return new Response(JSON.stringify({
      fund: { code: fund.code, name: fund.name, index_type: fund.index_type },
      params: { years, budget },
      simulation,
      note: simulation ? '基于预计算策略数据的近似结果' : '该基金未包含在预计算策略中',
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
