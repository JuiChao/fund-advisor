// GET /api/portfolio?years=20&budget=2000
// 返回3种策略 × 2种子方案（理论最优 + 实际可买）
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const years = Math.max(5, Math.min(30, parseInt(url.searchParams.get('years')) || 20));
  const budget = Math.max(100, parseInt(url.searchParams.get('budget')) || 2000);
  const scale = budget / 1000;
  const yearKey = String(years);

  try {
    const simsUrl = new URL('/data/simulations.json', context.request.url).toString();
    const resp = await context.env.ASSETS.fetch(simsUrl);
    const data = await resp.json();

    const results = data.strategies.map(s => {
      function scaleVariant(variant) {
        if (!variant) return null;
        const yearData = variant.by_years?.[yearKey] || {};
        return {
          allocations: (variant.allocations || []).map(a => ({
            ...a,
            monthly: Math.round(a.monthly * scale),
            daily: +(a.daily * scale).toFixed(1),
          })),
          note: variant.note,
          simulation: yearData.median ? {
            totalInvested: Math.round((yearData.totalInvested || 0) * scale),
            medianFinal: Math.round(yearData.median * scale),
            meanFinal: Math.round((yearData.mean || yearData.median) * scale),
            p5: Math.round((yearData.p5 || 0) * scale),
            p25: Math.round((yearData.p25 || 0) * scale),
            p75: Math.round((yearData.p75 || 0) * scale),
            p95: Math.round((yearData.p95 || 0) * scale),
            annualReturn: yearData.annualReturn,
            meanReturnPct: yearData.meanReturnPct,
          } : null,
        };
      }

      return {
        key: s.key,
        name: s.name,
        description: s.description,
        icon: s.icon,
        nq_pct: s.nq_pct,
        ideal: scaleVariant(s.ideal),
        practical: scaleVariant(s.practical),
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
