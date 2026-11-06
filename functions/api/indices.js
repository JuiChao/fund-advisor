// GET /api/indices
// Cloudflare Pages Functions 边缘网关接口
// 聚合、清洗与格式化腾讯财经美股行情 (纳指100、标普500及QQQ/SPY ETF)
// 支持 Edge Cache 响应头与多级容灾降级

export async function onRequest(context) {
  const cacheHeaders = {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'public, max-age=15, s-maxage=20, stale-while-revalidate=40',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  };

  if (context.request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: cacheHeaders });
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const upstreamUrl = 'https://qt.gtimg.cn/q=usNDX,usINX,usQQQ,usSPY';
    const resp = await fetch(upstreamUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; Cloudflare-Pages-Edge/1.0; +https://cloudflare.com)',
        'Referer': 'https://finance.qq.com/'
      }
    });
    clearTimeout(timeoutId);

    if (!resp.ok) {
      throw new Error(`Upstream returned HTTP ${resp.status}`);
    }

    const arrayBuffer = await resp.arrayBuffer();
    let rawText = '';
    try {
      rawText = new TextDecoder('gbk').decode(arrayBuffer);
    } catch (e) {
      rawText = new TextDecoder('utf-8').decode(arrayBuffer);
    }

    const parsed = parseTencentQuoteText(rawText);
    if (!parsed || !parsed.indices || !parsed.indices.NDX || !parsed.indices.INX) {
      throw new Error('Failed to parse required indices from upstream payload');
    }

    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: cacheHeaders
    });
  } catch (err) {
    // 降级容灾：尝试从静态底表 /data/indices_fallback.json 读取
    try {
      if (context.env && context.env.ASSETS) {
        const fallbackUrl = new URL('/data/indices_fallback.json', context.request.url).toString();
        const fallbackResp = await context.env.ASSETS.fetch(fallbackUrl);
        if (fallbackResp.ok) {
          const fallbackData = await fallbackResp.json();
          return new Response(JSON.stringify(fallbackData), {
            status: 200,
            headers: cacheHeaders
          });
        }
      }
    } catch (fallbackErr) {
      // 忽略底表获取错误，直接使用内联兜底
    }

    // 终极静态内存保底
    const inlineFallback = getInlineFallback();
    return new Response(JSON.stringify(inlineFallback), {
      status: 200,
      headers: cacheHeaders
    });
  }
}

/**
 * 解析腾讯财经美股快照格式
 * 示例: v_usNDX="200~纳斯达克100~.NDX~27000.40~26629.81~27045.26~167368409~...~2026-11-06 09:36:19~370.59~1.39~27099.09~26952.60~USD~...";
 */
export function parseTencentQuoteText(text) {
  if (!text || typeof text !== 'string') return null;

  const rawMap = {};
  const lines = text.split(';');

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const match = trimmed.match(/v_us([A-Za-z0-9_]+)="([^"]*)"/);
    if (!match) continue;

    const symbol = match[1];
    const parts = match[2].split('~');
    if (parts.length < 35) continue;

    const price = parseFloat(parts[3]) || 0;
    const prevClose = parseFloat(parts[4]) || 0;
    const open = parseFloat(parts[5]) || 0;
    const volume = parseInt(parts[6], 10) || 0;
    const datetime = parts[30] || '';
    const change = parseFloat(parts[31]) || 0;
    const changePct = parseFloat(parts[32]) || 0;
    const high = parseFloat(parts[33]) || 0;
    const low = parseFloat(parts[34]) || 0;
    const extendedPrice = (parts[67] && !isNaN(parseFloat(parts[67]))) ? parseFloat(parts[67]) : null;

    rawMap[symbol] = {
      symbol,
      code: parts[2] || symbol,
      name: parts[1] || symbol,
      price,
      prev_close: prevClose,
      open,
      volume,
      datetime,
      change,
      change_pct: changePct,
      high,
      low,
      extended_price: extendedPrice
    };
  }

  const ndx = rawMap['NDX'];
  const inx = rawMap['INX'];
  const qqq = rawMap['QQQ'];
  const spy = rawMap['SPY'];

  if (!ndx || !inx) return null;

  function calcRangePct(price, low, high) {
    if (high <= low) return 50;
    if (price <= low) return 0;
    if (price >= high) return 100;
    const pct = Math.round(((price - low) / (high - low)) * 100);
    return Math.max(0, Math.min(100, pct));
  }

  const marketStatus = computeMarketStatus();

  return {
    success: true,
    timestamp: Date.now(),
    market_status: marketStatus,
    updated_at: ndx.datetime || inx.datetime || new Date().toISOString(),
    indices: {
      NDX: {
        symbol: '^NDX',
        name: '纳斯达克100',
        code: ndx.code || '.NDX',
        etf_symbol: 'QQQ',
        price: ndx.price,
        change: ndx.change,
        change_pct: ndx.change_pct,
        open: ndx.open,
        high: ndx.high,
        low: ndx.low,
        prev_close: ndx.prev_close,
        range_pct: calcRangePct(ndx.price, ndx.low, ndx.high),
        extended_price: ndx.extended_price,
        etf_price: qqq ? qqq.price : null,
        etf_change: qqq ? qqq.change : null,
        etf_change_pct: qqq ? qqq.change_pct : null,
        datetime: ndx.datetime
      },
      INX: {
        symbol: '^GSPC',
        name: '标普500',
        code: inx.code || '.INX',
        etf_symbol: 'SPY',
        price: inx.price,
        change: inx.change,
        change_pct: inx.change_pct,
        open: inx.open,
        high: inx.high,
        low: inx.low,
        prev_close: inx.prev_close,
        range_pct: calcRangePct(inx.price, inx.low, inx.high),
        extended_price: inx.extended_price,
        etf_price: spy ? spy.price : null,
        etf_change: spy ? spy.change : null,
        etf_change_pct: spy ? spy.change_pct : null,
        datetime: inx.datetime
      }
    },
    raw: rawMap
  };
}

function isUSMarketHoliday(year, month, day, weekday) {
  const isNth = (n, w) => weekday === w && (day - 7 * (n - 1) > 0 && day - 7 * (n - 1) <= 7);
  const isLast = (w) => weekday === w && (day + 7 > new Date(year, month, 0).getDate());
  const isObs = (m, d) => (month === m && day === d && weekday !== 'Sat' && weekday !== 'Sun')
    || (month === m && day === d + 1 && weekday === 'Mon')
    || (month === m && day === d - 1 && weekday === 'Fri');

  if (isObs(1, 1)) return true; // New Year's Day
  if (month === 1 && isNth(3, 'Mon')) return true; // MLK Day
  if (month === 2 && isNth(3, 'Mon')) return true; // Presidents' Day
  if (month === 5 && isLast('Mon')) return true; // Memorial Day
  if (isObs(6, 19)) return true; // Juneteenth
  if (isObs(7, 4)) return true; // Independence Day
  if (month === 9 && isNth(1, 'Mon')) return true; // Labor Day
  if (month === 11 && isNth(4, 'Thu')) return true; // Thanksgiving Day
  if (isObs(12, 25)) return true; // Christmas Day
  return false;
}

/**
 * 依据美东时间精确判定交易时段
 */
function computeMarketStatus() {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/New_York',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      weekday: 'short',
      hour: 'numeric',
      minute: 'numeric',
      hour12: false
    });
    const parts = formatter.formatToParts(new Date());
    let year = 2026;
    let month = 1;
    let day = 1;
    let weekday = '';
    let hour = 0;
    let minute = 0;
    for (const p of parts) {
      if (p.type === 'year') year = parseInt(p.value, 10);
      if (p.type === 'month') month = parseInt(p.value, 10);
      if (p.type === 'day') day = parseInt(p.value, 10);
      if (p.type === 'weekday') weekday = p.value;
      if (p.type === 'hour') hour = parseInt(p.value, 10);
      if (p.type === 'minute') minute = parseInt(p.value, 10);
    }
    if (hour === 24) hour = 0;
    const isWeekend = (weekday === 'Sat' || weekday === 'Sun');
    const isHoliday = isUSMarketHoliday(year, month, day, weekday);
    const totalMin = hour * 60 + minute;

    if (isWeekend || isHoliday) return 'CLOSED';
    if (totalMin >= 9 * 60 + 30 && totalMin < 16 * 60) return 'REGULAR';
    if (totalMin >= 4 * 60 && totalMin < 9 * 60 + 30) return 'PRE-MARKET';
    if (totalMin >= 16 * 60 && totalMin < 20 * 60) return 'AFTER-HOURS';
    return 'CLOSED';
  } catch (e) {
    return 'UNKNOWN';
  }
}

function getInlineFallback() {
  return {
    success: true,
    timestamp: Date.now(),
    market_status: 'CLOSED',
    fallback: true,
    updated_at: '2026-11-06 16:00:00',
    indices: {
      NDX: {
        symbol: '^NDX',
        name: '纳斯达克100',
        code: '.NDX',
        etf_symbol: 'QQQ',
        price: 26958.76,
        change: 328.95,
        change_pct: 1.24,
        open: 27045.26,
        high: 27099.09,
        low: 26952.60,
        prev_close: 26629.81,
        range_pct: 4,
        extended_price: 26958.76,
        etf_price: 655.74,
        etf_change: 8.69,
        etf_change_pct: 1.34,
        datetime: '2026-11-06 16:00:00'
      },
      INX: {
        symbol: '^GSPC',
        name: '标普500',
        code: '.INX',
        etf_symbol: 'SPY',
        price: 7374.71,
        change: 20.98,
        change_pct: 0.29,
        open: 7377.65,
        high: 7389.04,
        low: 7369.55,
        prev_close: 7353.73,
        range_pct: 26,
        extended_price: 7374.71,
        etf_price: 735.21,
        etf_change: 2.21,
        etf_change_pct: 0.30,
        datetime: '2026-11-06 16:00:00'
      }
    }
  };
}
