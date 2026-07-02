// GET /api/portfolio?years=20&budget=2000
// 查表 + 线性缩放，返回6种策略结果
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const years = Math.max(5, Math.min(30, parseInt(url.searchParams.get('years')) || 20));
  const budget = Math.max(100, parseInt(url.searchParams.get('budget')) || 2000);
  const scale = budget / 1000; // 基准预算1000元

  try {
    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const resp = await context.env.ASSETS.fetch(simsUrl);
    const data = await resp.json();
    const yearKey = String(years);

    const results = data.strategies.map(s => {
      const yearData = s.by_years?.[yearKey] || {};
      return {
        key: s.key,
        name: s.name,
        description: s.description,
        allocations: (s.allocations || []).map(a => ({
          ...a,
          monthly: Math.round(a.monthly * scale),
          daily: +(a.daily * scale).toFixed(1),
        })),
        simulation: yearData.medianFinal ? {
          totalInvested: Math.round(yearData.totalInvested * scale),
          medianFinal: Math.round(yearData.medianFinal * scale),
          meanFinal: Math.round((yearData.meanFinal || yearData.medianFinal) * scale),
          p5: Math.round(yearData.p5 * scale),
          p25: Math.round(yearData.p25 * scale),
          p75: Math.round(yearData.p75 * scale),
          p95: Math.round(yearData.p95 * scale),
          annualReturn: yearData.annualReturn,
          meanReturnPct: yearData.meanReturnPct,
        } : null,
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
