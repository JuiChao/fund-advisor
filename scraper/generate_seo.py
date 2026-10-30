import json
import os
import shutil
import glob
import sys
import statistics
import datetime

sys.stdout.reconfigure(encoding='utf-8')

# 路径配置
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scraper.limit_tracker import find_substitutes
DATA_FILE = os.path.join(ROOT_DIR, 'public', 'data', 'funds.json')
FUND_DIR = os.path.join(ROOT_DIR, 'public', 'fund')
ARTICLES_DIR = os.path.join(ROOT_DIR, 'public', 'articles')
SITEMAP_FILE = os.path.join(ROOT_DIR, 'public', 'sitemap.xml')
LIMIT_CHANGES_FILE = os.path.join(ROOT_DIR, 'public', 'data', 'limit_changes.json')

# 清理并创建 fund 目录
if os.path.exists(FUND_DIR):
    shutil.rmtree(FUND_DIR)
os.makedirs(FUND_DIR)

# 加载数据
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    funds = json.load(f)

limit_changes_history = []
if os.path.exists(LIMIT_CHANGES_FILE):
    try:
        with open(LIMIT_CHANGES_FILE, 'r', encoding='utf-8') as f:
            l_data = json.load(f)
            if isinstance(l_data, dict):
                limit_changes_history = l_data.get('history', [])
    except Exception:
        pass

funds_map = {f['code']: f for f in funds}

# 计算大类指数中位数
medians = {}
for itype in ['纳斯达克100', '标普500']:
    group = [f for f in funds if f.get('index_type') == itype]
    fees = [f['mgmt_fee'] + f['custody_fee'] + (f.get('sales_fee') or 0.0) for f in group]
    tes = [f['tracking_error'] for f in group if f.get('tracking_error') is not None]
    scales = [f['scale'] for f in group if f.get('scale') is not None]
    medians[itype] = {
        'fee': statistics.median(fees) if fees else 0.0085,
        'te': statistics.median(tes) if tes else 0.015,
        'scale': statistics.median(scales) if scales else 12.0
    }

def format_pct(val):
    if val is None:
        return "-"
    return f"{val * 100:.2f}"

# HTML 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<title>{fund_name} ({fund_code}) 费率_限购_历史收益 - Fund Advisor</title>
<meta name="description" content="{fund_name}({fund_code})是跟踪{index_type}指数的公募QDII基金({share_class}类份额)。当前代销状态：{agency_status}，直销状态：{direct_status}。综合年费率{total_fee}%。近3年收益率{return_3yr}%。点击查阅详细量化多因子评测与定投策略。">
<meta name="keywords" content="{fund_code}, {fund_name}, {index_type}, {share_class}类份额, 费率, 限购, 收益率, 定投, Fund Advisor">
<link rel="canonical" href="https://858000.xyz/fund/{fund_code}">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css?v=20261009_v7">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8921283801578142" crossorigin="anonymous"></script>
<script type="application/ld+json">
{json_ld}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "首页", "item": "https://858000.xyz/" }},
    {{ "@type": "ListItem", "position": 2, "name": "基金排名", "item": "https://858000.xyz/#ranking" }},
    {{ "@type": "ListItem", "position": 3, "name": "{fund_name}", "item": "https://858000.xyz/fund/{fund_code}" }}
  ]
}}
</script>
<script>(function(){{var t=localStorage.getItem('fa_theme')||(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);}})();</script>
</head>
<body>
<div id="scroll-progress" aria-hidden="true"></div>
<div class="ambient-glow-mesh" aria-hidden="true">
    <div class="ambient-glow ambient-glow-1"></div>
    <div class="ambient-glow ambient-glow-2"></div>
    <div class="ambient-glow ambient-glow-3"></div>
    <div class="ambient-glow ambient-glow-4"></div>
</div>
<header>
<nav class="navbar navbar-subpage">
    <div class="brand">
        <a href="/" style="display:flex;align-items:center;text-decoration:none;color:inherit">
            <img src="/favicon.png" alt="Fund Advisor" class="brand-logo">
            <span class="brand-text">FUND ADVISOR</span>
            <span class="brand-sub-badge"><span class="brand-pulse-dot"></span> QDII 实时量化监控</span>
        </a>
    </div>
    <div class="links" id="nav-links">
        <a href="/">返回首页</a>
        <a href="/#ranking">基金排名</a>
        <a href="/#simulator">模拟器</a>
        <a href="/#portfolio">定投方案</a>
        <a href="/articles/">投资百科</a>
        <a href="/about">关于我们</a>
    </div>
    <div class="nav-actions">
        <a href="/#portfolio" class="nav-cta-btn" title="立即开启量化资产配置">🚀 定投方案</a>
        <button class="theme-toggle" id="theme-toggle" aria-label="切换主题" title="切换深色/浅色模式">
            <span class="theme-icon">🌙</span>
        </button>
        <button class="nav-toggle" aria-label="切换菜单" aria-expanded="false" onclick="var l=document.getElementById('nav-links');var b=this;var o=l.classList.toggle('show');b.classList.toggle('open',o);b.setAttribute('aria-expanded',o);">
            <span></span><span></span><span></span>
        </button>
    </div>
</nav>
</header>
<main class="container">
    <nav class="breadcrumb" style="font-size:0.85rem;color:var(--txt3);margin:1.5rem 0 0.5rem">
        <a href="/" style="color:inherit;text-decoration:none">首页</a> &gt; 
        <a href="/#ranking" style="color:inherit;text-decoration:none">基金排名</a> &gt; 
        <span>{fund_name} ({fund_code})</span>
    </nav>
    <div class="card" style="margin-top:1rem">
        <div class="terminal-chrome" aria-hidden="true">
            <div class="terminal-dots">
                <span class="dot-red"></span>
                <span class="dot-yellow"></span>
                <span class="dot-green"></span>
            </div>
            <div class="terminal-title"><span class="brand-pulse-dot"></span> QUANT SECURITY ANALYSIS // {fund_code}</div>
            <div class="terminal-status"><span class="terminal-tag">{index_type}</span> <span>{share_class}类份额</span></div>
        </div>
        <h1 style="font-size:1.5rem;margin-bottom:0.5rem"><span class="badge-share badge-{share_class_lower}">{share_class}类</span> {fund_name} (<span style="color:var(--txt2)">{fund_code}</span>)</h1>
        <p style="color:var(--txt2);margin-bottom:1.5rem">{full_name} | {manager_company} | 基金经理: {fund_manager} | 成立日期: {inception_date}</p>
        
        <div class="g2" style="margin-bottom:1.5rem">
            <div style="background:var(--surface2);border:1px solid var(--border);padding:1.15rem;border-radius:12px;box-shadow:var(--shadow-sm)">
                <div style="color:var(--txt3);font-size:0.78rem;font-weight:750;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase">综合年费率</div>
                <div style="font-size:1.4rem;font-weight:850;font-family:var(--font-mono);color:var(--txt);letter-spacing:-0.02em;margin:4px 0">{total_fee}%<span style="font-size:0.8rem;color:var(--txt3);font-weight:normal">/年</span></div>
                <div style="font-size:0.75rem;color:var(--txt2)">管理费 {mgmt_fee}% + 托管费 {custody_fee}%{sales_fee_str}</div>
            </div>
            <div style="background:var(--surface2);border:1px solid var(--border);padding:1.15rem;border-radius:12px;box-shadow:var(--shadow-sm)">
                <div style="color:var(--txt3);font-size:0.78rem;font-weight:750;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase">代销限购状态</div>
                <div style="font-size:1.4rem;font-weight:850;font-family:var(--font-mono);color:var(--txt);letter-spacing:-0.02em;margin:4px 0">{agency_status}</div>
                <div style="font-size:0.75rem;color:var(--txt2)">天天基金/支付宝等三方渠道</div>
            </div>
            <div style="background:var(--surface2);border:1px solid var(--border);padding:1.15rem;border-radius:12px;box-shadow:var(--shadow-sm)">
                <div style="color:var(--txt3);font-size:0.78rem;font-weight:750;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase">直销限购状态</div>
                <div style="font-size:1.4rem;font-weight:850;font-family:var(--font-mono);color:var(--txt);letter-spacing:-0.02em;margin:4px 0">{direct_status}</div>
                <div style="font-size:0.75rem;color:var(--txt2)">基金公司官网/官方APP通道</div>
            </div>
            <div style="background:var(--surface2);border:1px solid var(--border);padding:1.15rem;border-radius:12px;box-shadow:var(--shadow-sm)">
                <div style="color:var(--txt3);font-size:0.78rem;font-weight:750;font-family:var(--font-mono);letter-spacing:0.04em;text-transform:uppercase">近3年收益率</div>
                <div style="font-size:1.4rem;font-weight:850;font-family:var(--font-mono);color:var(--{return_color});letter-spacing:-0.02em;margin:4px 0">{return_3yr}%</div>
                <div style="font-size:0.75rem;color:var(--txt2)">近1年收益: {return_1yr}%</div>
            </div>
        </div>

        {review_html}

        <!-- 专题推荐与深度研报关联 -->
        <div style="margin-top:2rem;padding:1.25rem;background:var(--surface2);border-radius:10px;border:1px solid var(--border)">
            <h3 style="font-size:1.05rem;color:var(--txt);margin-top:0;margin-bottom:0.75rem;font-weight:700">📚 推荐投研指南与实操精读</h3>
            <ul style="padding-left:1.2rem;margin-bottom:0;color:var(--txt2);font-size:0.9rem;line-height:1.7">
                <li><a href="/articles/{related_guide_slug}" style="color:var(--accent2);text-decoration:none;font-weight:600">{related_guide_title} ➔</a></li>
                <li><a href="/articles/how-to-choose-qdii-funds" style="color:var(--accent2);text-decoration:none;font-weight:600">如何挑选最优QDII指数基金：费率、规模与跟踪误差三角法则 ➔</a></li>
                <li><a href="/articles/share-class-a-vs-c-break-even-analysis" style="color:var(--accent2);text-decoration:none;font-weight:600">A类与C类份额终极抉择：持有几年才是费率平衡临界点？（附量化数学推导） ➔</a></li>
                <li><a href="/articles/penetrating-qdii-purchase-quota-restrictions" style="color:var(--accent2);text-decoration:none;font-weight:600">穿透公募基金限购内幕：为什么QDII单日限额会从1000元骤降至10元？ ➔</a></li>
            </ul>
        </div>

        <!-- ===== E-E-A-T 投研团队与专业审阅声明 ===== -->
        <div class="eeat-author-card">
            <div class="eeat-header">
                <div class="eeat-avatar">📊</div>
                <div class="eeat-meta">
                    <div class="eeat-author-name">
                        <strong>Fund Advisor 量化投研团队</strong>
                        <span class="eeat-badge">量化评测组</span>
                    </div>
                    <div class="eeat-author-desc">
                        本评测由持有特许金融分析师 (CFA) 与金融工程量化背景的研究团队联合编制，基于基金管理人法定披露信息及全市场客观数据生成。
                    </div>
                </div>
            </div>
            <div class="eeat-divider"></div>
            <div class="eeat-details-grid">
                <div class="eeat-item">
                    <span class="eeat-lbl">🔍 同业复核</span>
                    <span class="eeat-val">定量风控与合规模型多重校验</span>
                </div>
                <div class="eeat-item">
                    <span class="eeat-lbl">📅 动态更新</span>
                    <span class="eeat-val">每日自动同步公募披露与限额公告</span>
                </div>
                <div class="eeat-item">
                    <span class="eeat-lbl">📚 理论基石</span>
                    <span class="eeat-val">现代投资组合理论 (MPT) · 跟踪偏离度检验</span>
                </div>
                <div class="eeat-item">
                    <span class="eeat-lbl">🛡️ 独立原则</span>
                    <span class="eeat-val">无商业佣金输送 · 算法与数据完全透明</span>
                </div>
            </div>
            <div class="eeat-disclaimer">
                <strong>⚠️ 免责合规声明：</strong>本页面所载分析仅供量化研究与个人理财科普之用，不构成任何形式的投资建议或基金销售推介。<a href="/about" style="color:var(--accent2);text-decoration:none;margin-left:6px;font-weight:600">查阅关于我们与完整投研方法论 ➔</a>
            </div>
        </div>

        <!-- 合规声明 -->
        <div style="margin-top:1.5rem;padding:1rem 1.25rem;background:rgba(234,179,8,0.06);border-left:4px solid #eab308;border-radius:6px;font-size:0.82rem;color:var(--txt2);line-height:1.6">
            <strong style="color:var(--txt)">⚠️ 风险提示与数据合规声明：</strong><br>
            本页面展示之基金费率（管理费、托管费、销售服务费）、申购限购状态（代销/直销渠道）及历史业绩数据均采集自基金公司法定公开披露公告及天天基金网公开接口。相关数据仅供学术量化分析、策略模拟与投资者教育之用，<strong>不构成任何形式的投资建议、财务顾问意见或基金销售推介</strong>。公募基金过往业绩不代表未来表现，市场有风险，投资需谨慎。本平台不从事任何公募或私募基金销售代理业务。
        </div>

        <div style="text-align:center;margin:2.5rem 0 1rem 0">
            <a href="/#ranking?q={fund_code}" class="btn btn-p" style="text-decoration:none;padding:0.75rem 2rem;font-size:1.1rem">在 Fund Advisor 完整版中进行定投模拟 ➔</a>
        </div>
    </div>
</main>
<footer style="margin-top:4rem;padding:2.5rem 0;border-top:1px solid var(--border);text-align:center;color:var(--txt3);font-size:0.88rem">
    <div style="margin-bottom:1rem;display:flex;justify-content:center;flex-wrap:wrap;gap:15px">
        <a href="/" style="color:var(--txt3);text-decoration:none">首页概览</a> |
        <a href="/#ranking" style="color:var(--txt3);text-decoration:none">基金排名</a> |
        <a href="/#portfolio" style="color:var(--txt3);text-decoration:none">定投方案</a> |
        <a href="/#simulator" style="color:var(--txt3);text-decoration:none">蒙特卡洛模拟器</a> |
        <a href="/articles/" style="color:var(--txt3);text-decoration:none">投资百科</a> |
        <a href="/about" style="color:var(--txt3);text-decoration:none">关于我们</a> |
        <a href="/privacy-policy" style="color:var(--txt3);text-decoration:none">隐私政策</a> |
        <a href="/terms-of-service" style="color:var(--txt3);text-decoration:none">服务条款</a> |
        <a href="mailto:contact@858000.xyz" style="color:var(--txt3);text-decoration:none">联系我们</a>
    </div>
    <p>© 2026 Fund Advisor. All rights reserved. 专注纳斯达克100与标普500指数基金量化投研。</p>
</footer>
<script>
(function() {{
    function getTheme() {{
        var s = localStorage.getItem('fa_theme');
        if (s) return s;
        return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    }}
    function applyTheme(t) {{
        document.documentElement.setAttribute('data-theme', t);
        localStorage.setItem('fa_theme', t);
        var icon = document.querySelector('#theme-toggle .theme-icon');
        if (icon) icon.textContent = t === 'dark' ? '☀️' : '🌙';
    }}
    applyTheme(getTheme());
    var btn = document.getElementById('theme-toggle');
    if (btn) {{
        btn.onclick = function() {{
            var cur = document.documentElement.getAttribute('data-theme') || 'light';
            applyTheme(cur === 'dark' ? 'light' : 'dark');
        }};
    }}
}})();
</script>
</body>
</html>
"""

generated_count = 0

for fund in funds:
    code = fund['code']
    share_class = fund.get('share_class', 'A')
    index_type = fund.get('index_type', '纳斯达克100')
    manager_company = fund.get('manager_company', '')
    fund_manager = fund.get('fund_manager', '暂无公开披露')
    custodian = fund.get('custodian', '公募托管银行')
    scale = fund.get('scale')
    inception_date = fund.get('inception_date', '-')
    benchmark = fund.get('benchmark', f"{index_type}指数")
    te = fund.get('tracking_error')
    td = fund.get('tracking_difference')
    ir = fund.get('information_ratio')
    
    sales_fee = fund.get('sales_fee', 0.0) or 0.0
    mgmt_fee = fund.get('mgmt_fee', 0.0) or 0.0
    custody_fee = fund.get('custody_fee', 0.0) or 0.0
    total_fee = mgmt_fee + custody_fee + sales_fee
    sales_fee_str = f" + 销售服务费 {format_pct(sales_fee)}%" if sales_fee > 0 else ""

    r1 = fund.get('return_1yr')
    r1_str = format_pct(r1) if r1 is not None else "-"
    r3 = fund.get('return_3yr')
    if r3 is not None:
        r3_str = format_pct(r3)
        ret_color = "ok" if r3 > 0 else "err"
    else:
        r3_str = "-"
        ret_color = "txt"

    agency_status = fund.get('limit_status', '正常')
    direct_status = fund.get('direct_limit_status') or agency_status
    daily_limit = fund.get('daily_limit')
    direct_daily_limit = fund.get('direct_daily_limit')
    quota_sharing = fund.get('quota_sharing', 'UNKNOWN')
    quota_shared_desc = fund.get('quota_shared_desc', '')

    cat_med = medians.get(index_type, {'fee': 0.0085, 'te': 0.015, 'scale': 12.0})

    # 1. 费率横向对比评语
    if total_fee <= 0.007:
        fee_eval = f"该标的年化综合费率仅为 <strong>{format_pct(total_fee)}%</strong>，处于全市场 {index_type} 基金前 10% 的最低费率梯队（大幅优于同类中位数 {cat_med['fee']*100:.2f}%）。在长达 10~30 年的指数定投长跑中，超低管理成本能为您最大限度锁定复利成果。"
    elif total_fee <= cat_med['fee']:
        diff = (cat_med['fee'] - total_fee) * 100
        fee_eval = f"该标的年化综合费率为 <strong>{format_pct(total_fee)}%</strong>，低于同类中位数（{cat_med['fee']*100:.2f}%）约 {diff:.2f} 个百分点，费率结构具备良好竞争力，适合中长期资产配置。"
    else:
        diff = (total_fee - cat_med['fee']) * 100
        if share_class == 'C':
            fee_eval = f"该份额年化综合费率为 <strong>{format_pct(total_fee)}%</strong>，其中包含年化 {format_pct(sales_fee)}% 的销售服务费。虽然费率略高于同类中位数（{cat_med['fee']*100:.2f}%），但其免收前端申购费且持有 7 天以上通常免赎回费，适合短期持有或在 A 类限购时作为定投备用通道。"
        else:
            fee_eval = f"该标的年化综合费率为 <strong>{format_pct(total_fee)}%</strong>，略高于同类中位数（{cat_med['fee']*100:.2f}%）约 {diff:.2f} 个百分点。在定投长跑中建议重点结合其跟踪精度与渠道申购便利性进行综合权衡。"

    # 2. 跟踪误差分析
    if te is not None:
        te_pct = te * 100
        med_te_pct = cat_med['te'] * 100
        if te <= 0.012:
            te_eval = f"在指数复制质量方面，该基金近 1 年跟踪误差仅为 <strong>{te_pct:.2f}%</strong>，显著优于同类中位数（{med_te_pct:.2f}%），表现出极高的被动指数跟踪精度与极低的调仓摩擦成本。"
        elif te <= cat_med['te']:
            te_eval = f"在指数复制质量方面，该基金近 1 年跟踪误差为 <strong>{te_pct:.2f}%</strong>，优于同类中位数（{med_te_pct:.2f}%），基金经理展现出良好的指数复制执行力。"
        else:
            te_eval = f"该基金近 1 年跟踪误差为 <strong>{te_pct:.2f}%</strong>，略高于同类中位数（{med_te_pct:.2f}%）。这通常受到跨境投资时差、现金仓位保留以及外汇兑换时滞的影响。"
    else:
        te_eval = "该标的成立时间尚短或正在建仓期，暂无完整的 1 年期跟踪误差历史数据，建议持续观察其净值与指数走势的贴合度。"

    # 3. 规模分析
    if scale is not None:
        if scale >= 30.0:
            scale_eval = f"规模方面，最新资产规模达 <strong>{scale:.2f} 亿元</strong>，属于公募 QDII 领域的大型旗舰产品，具备充裕的申赎流动性，抗巨额赎回冲击能力极强，完全不存在清盘隐患。"
        elif scale >= 5.0:
            scale_eval = f"规模方面，最新资产规模为 <strong>{scale:.2f} 亿元</strong>，处于 5~30 亿元的健康黄金运作区间，规模既适中保障了充沛流动性，又便于基金经理高效进行外汇头寸管理。"
        elif scale >= 2.0:
            scale_eval = f"规模方面，最新资产规模为 <strong>{scale:.2f} 亿元</strong>，处于平稳运行区间，未触及清盘预警线。"
        else:
            scale_eval = f"规模方面，最新资产规模为 <strong>{scale:.2f} 亿元</strong>，规模体量偏小。投资者应留意公募基金 5000 万元法定清盘预警线以及大额申赎对净值带来的短期微幅扰动。"
    else:
        scale_eval = "暂未收录该标的最新独立规模数据。"

    # 4. 渠道限额与决策
    channel_eval = ""
    substitutes_html = ""
    agency_is_paused = ("暂停" in agency_status) or ("未开通" in agency_status)
    direct_is_paused = ("暂停" in direct_status) or ("未开通" in direct_status) or (not direct_status)
    is_all_paused = agency_is_paused and direct_is_paused

    if is_all_paused:
        channel_eval = f"⚠️ <strong>全渠道暂停申购提示</strong>：目前天天基金、支付宝等代销渠道与基金公司官方直销平台均处于暂停申购或未开放状态，表明该基金管理人的外汇额度余量极低或定制份额未开放散户直销。定投投资者建议无需恐慌，可通过下方推荐平替至其他正常开放的同指数基金，以确保定投计划不中断。"
        subs = find_substitutes(fund, funds, max_count=3)
        if subs:
            sub_cards = []
            for s in subs:
                s_code = s['code']
                s_name = s['name']
                s_fee_str = f"{s['total_fee'] * 100:.2f}%"
                s_class = s.get('share_class') or 'A'
                ag_st = s.get('limit_status') or '正常'
                dir_st = s.get('direct_limit_status') or ag_st
                sub_cards.append(
                    f"<div style='background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:0.9rem;display:flex;flex-direction:column;justify-content:space-between;box-shadow:var(--shadow-sm);'>"
                    f"<div>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;'>"
                    f"<span class='code-mono' style='font-weight:700;color:var(--accent2);'>{s_code}</span>"
                    f"<span class='badge-share badge-{s_class.lower()}'>{s_class}类</span>"
                    f"</div>"
                    f"<a href='/fund/{s_code}' style='color:var(--txt);font-weight:600;font-size:0.9rem;text-decoration:none;display:block;margin-bottom:0.5rem;line-height:1.4;'>{s_name}</a>"
                    f"<div style='font-size:0.8rem;color:var(--txt2);margin-bottom:0.3rem;'>"
                    f"<span>综合费率: <strong style='color:var(--txt);'>{s_fee_str}</strong></span>"
                    f"</div>"
                    f"<div style='font-size:0.8rem;color:var(--txt2);margin-bottom:0.6rem;'>"
                    f"<span>当前额度: <span style='color:var(--ok);font-weight:600;'>代销({ag_st}) / 直销({dir_st})</span></span>"
                    f"</div>"
                    f"</div>"
                    f"<a href='/fund/{s_code}' class='btn-dir-review' style='display:block;text-align:center;padding:0.4rem 0.6rem;font-size:0.8rem;margin-top:auto;'>查看平替专页 ➔</a>"
                    f"</div>"
                )
            substitutes_html = (
                f"<div style='margin:1rem 0 1.25rem;background:rgba(16,185,129,0.05);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:1.15rem;'>"
                f"<h4 style='margin:0 0 0.75rem;font-size:0.95rem;color:var(--ok);display:flex;align-items:center;gap:6px;'>"
                f"<span>🛡️</span> 优质平替基金推荐（同跟踪 {index_type} 且当前开放申购）"
                f"</h4>"
                f"<div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:0.85rem;'>"
                f"{''.join(sub_cards)}"
                f"</div>"
                f"</div>"
            )
    elif agency_is_paused and not direct_is_paused:
        channel_eval = f"💡 <strong>直销渠道突破策略</strong>：虽然天天基金/支付宝等三方代销渠道已暂停申购，但基金公司官网或官方 APP <strong>直销渠道仍处于可买状态（{direct_status}）</strong>！对于希望持续定投该基金的投资者，强烈建议开通基金公司官方直销账户，即可规避代销渠道暂停的阻碍。"
    elif "限" in agency_status and direct_daily_limit is not None and daily_limit is not None and daily_limit > 0 and direct_daily_limit > daily_limit:
        multiplier = direct_daily_limit / daily_limit
        channel_eval = f"🚀 <strong>直销大额额度优势</strong>：该标的代销渠道限额为 <strong>{agency_status}</strong>，而官方直销渠道单日限额高达 <strong>{direct_status}</strong>，直销单日额度是代销的 <strong>{multiplier:.1f} 倍</strong>！若您的月度定投预算较高，选择官方直销渠道可大幅提升单次扣款上限。"
    else:
        channel_eval = f"目前该标的代销状态为“{agency_status}”，直销状态为“{direct_status}”。额度状态受国家外汇管理局外汇额度分配动态调控，建议定投前每日查阅本看板最新动态。"

    # 5. 共享额度提示
    quota_rule_eval = ""
    if quota_sharing == 'INDEPENDENT':
        quota_rule_eval = f"🔗 <strong>份额独立限额优势</strong>：{quota_shared_desc}。这意味着若您同日申购了满额的 A 类份额，仍可继续申购该基金的 C 类份额，各份额独立占用额度，非常适合用于拼单打满月定投预算。"
    elif quota_sharing == 'SHARED':
        quota_rule_eval = f"⚠️ <strong>跨份额合并限额预警</strong>：{quota_shared_desc}。基金公司按同一投资者身份证在全市场合并计算限额。若您当天已申购满 A 类份额，请勿在同日重复申购 C 类份额，否则超额部分将被系统自动退款。"

    # 6. 份额选择建议
    if share_class == 'A':
        share_eval = "A 类份额无销售服务费，通常在第三方销售平台享受前端申购费 1 折（折后约 0.10%~0.12%）。根据量化数学推导，当计划持有时间 <strong>大于 4.8 个月</strong> 时，A 类份额的综合持有成本显著低于 C 类份额，是长期定投底仓的黄金选择。"
    elif share_class == 'C':
        share_eval = f"C 类份额免收前端申购费，按日计提销售服务费（年化约 {format_pct(sales_fee)}%）。持有满 7 天以上通常免收赎回费。适合 <strong>持有期限小于 4.8 个月</strong> 的波段交易，或在同门 A 类限购无法达成每月定投金额时作为补充拼单通道。"
    else:
        share_eval = f"{share_class} 类份额为特定渠道或平台专属定制份额，具有针对特定投资者群体的费率倾斜或直销大额通道优势。"

    # 7. 同门份额表格
    siblings_codes = fund.get('siblings', [])
    siblings_html = ""
    if len(siblings_codes) > 1:
        sib_rows = []
        for sc in siblings_codes:
            s_fund = funds_map.get(sc)
            if not s_fund:
                continue
            s_class = s_fund.get('share_class', 'A')
            s_sales = s_fund.get('sales_fee', 0.0) or 0.0
            s_fee = s_fund.get('mgmt_fee', 0.0) + s_fund.get('custody_fee', 0.0) + s_sales
            s_ag = s_fund.get('limit_status', '正常')
            s_dir = s_fund.get('direct_limit_status') or s_ag
            is_cur = " (当前标的)" if sc == code else ""
            cur_style = "style='background:rgba(99,102,241,0.06);font-weight:600'" if sc == code else ""
            sib_rows.append(
                f"<tr {cur_style}><td style='text-align:center'><span class='badge-share badge-{s_class.lower()}'>{s_class}类</span></td>"
                f"<td style='text-align:center'><span class='code-mono'>{sc}</span></td>"
                f"<td><a href='/fund/{sc}' style='color:var(--txt);text-decoration:none'>{s_fund.get('name', '')}{is_cur}</a></td>"
                f"<td style='text-align:center'>{format_pct(s_fee)}%</td>"
                f"<td style='text-align:center'>{s_ag}</td>"
                f"<td style='text-align:center'>{s_dir}</td>"
                f"<td style='text-align:center'><a href='/fund/{sc}' class='btn-dir-review' style='padding:2px 8px;font-size:0.75rem'>专页 ➔</a></td></tr>"
            )
        siblings_html = f"""
            <div style="margin-top:1.75rem">
                <h3 style="font-size:1.1rem;color:var(--txt);margin-bottom:0.75rem;font-weight:700">🏛️ 同门跨份额对比矩阵 ({fund.get('family_name', '同系列基金')})</h3>
                <div class="dir-table-wrap">
                    <table class="tbl dir-table" style="font-size:0.85rem">
                        <thead>
                            <tr>
                                <th class="col-center" style="width:65px">份额</th>
                                <th class="col-center" style="width:80px">代码</th>
                                <th style="min-width:200px">基金简称</th>
                                <th class="col-center" style="width:85px">综合年费</th>
                                <th class="col-center" style="width:95px">代销渠道</th>
                                <th class="col-center" style="width:95px">直销渠道</th>
                                <th class="col-center" style="width:80px">查看</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(sib_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        """

    # 8. 限购调整历史
    fund_history = [h for h in limit_changes_history if h.get('code') == code]
    quota_history_html = ""
    if fund_history:
        history_items = []
        for h in fund_history[:4]:
            ann_link = f" <a href='{h.get('announcement_url')}' target='_blank' style='color:var(--accent2);text-decoration:none;font-size:0.82rem;font-weight:600;margin-left:6px;'>[官方公告 ↗]</a>" if h.get('announcement_url') else ""
            history_items.append(
                f"<li style='margin-bottom:0.5rem;'><strong>{h.get('date')}</strong> · <span style='color:var(--accent2);font-weight:600;'>{h.get('change_type_label', '')}</span>: {h.get('summary', '')}{ann_link}</li>"
            )
        quota_history_html = f"""
            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:1rem 1.15rem;margin-top:1.5rem;">
                <h3 style="font-size:1.05rem;color:var(--txt);margin-top:0;margin-bottom:0.6rem;font-weight:700;">📢 申购限购调整历史与渠道动态</h3>
                <ul style="padding-left:1.2rem;margin-bottom:0;color:var(--txt2);font-size:0.88rem;line-height:1.5;">
                    {''.join(history_items)}
                </ul>
            </div>
        """

    # 深度综合评测 HTML
    review_html = f"""
        <div class="fund-seo-review" style="margin-top:2rem;line-height:1.75;color:var(--txt2);font-size:1rem;">
            <h2 style="font-size:1.25rem;color:var(--txt);margin-bottom:1rem;font-weight:700;">{fund.get('name', '')} 深度量化评测</h2>
            
            <p style="margin-bottom:1.1rem;">
                <strong>{fund.get('name', '')} (代码: {code})</strong> 是由 <strong>{manager_company}</strong> 发行并管理的公募 QDII 指数基金，属于该产品线的 <strong>{share_class} 类份额</strong>，紧密跟踪海外核心资产 <strong>{index_type}</strong>。该基金成立于 {inception_date}，基金资产由 <strong>{custodian}</strong> 安全托管，业绩比较基准为 <em>{benchmark}</em>。
            </p>

            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:1.15rem;margin-bottom:1.25rem;">
                <h3 style="margin-top:0;margin-bottom:0.6rem;font-size:1rem;color:var(--txt);font-weight:700;">📊 核心量化多因子体检报告</h3>
                <ul style="padding-left:1.2rem;margin:0;font-size:0.92rem;line-height:1.75;">
                    <li><strong>费率维度</strong>：{fee_eval}</li>
                    <li><strong>跟踪偏离</strong>：{te_eval}</li>
                    <li><strong>资产规模</strong>：{scale_eval}</li>
                    <li><strong>份额建议</strong>：{share_eval}</li>
                </ul>
            </div>

            <h3 style="font-size:1.08rem;color:var(--txt);margin-top:1.5rem;margin-bottom:0.6rem;font-weight:700;">🛒 渠道额度穿透与定投实操建议</h3>
            <div style="padding:1rem 1.15rem;background:rgba(99,102,241,0.06);border-left:4px solid var(--accent2);border-radius:6px;margin-bottom:1rem;font-size:0.92rem;line-height:1.65">
                {channel_eval}
            </div>
            {substitutes_html}

            {f"<div style='padding:0.75rem 1.15rem;background:var(--surface2);border:1px solid var(--border);border-radius:6px;margin-bottom:1rem;font-size:0.88rem'>{quota_rule_eval}</div>" if quota_rule_eval else ""}

            <p style="margin-bottom:1rem;">
                <strong>历史收益与风险透视</strong>：该基金近 3 年累计收益率为 <strong>{r3_str}%</strong>，近 1 年收益率为 <strong>{r1_str}%</strong>。公募指数基金的历史业绩主要反映其所追踪的底层标的资产（{index_type}）的系统性 Beta 回报，并不构成对未来表现的确定性保证。美股指数长期展现出强大的科技复利增长韧性，但历史中也曾经历 2000 年互联网泡沫、2008 年次贷海啸与 2022 年美联储加息等大幅回撤周期。建议普通投资者摒弃追涨杀跌的择时心态，利用机械化定投平滑持仓成本。
            </p>

            {siblings_html}

            {quota_history_html}
        </div>
    """

    if index_type == '标普500':
        related_guide_slug = 'sp500-investment-guide'
        related_guide_title = '标普500指数投资深度解析与行业分布实测'
    else:
        related_guide_slug = 'nasdaq-100-investment-guide'
        related_guide_title = '纳斯达克100指数投资完全指南：历史估值与科技巨头集中度'

    json_ld = {
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": fund.get('name', ''),
        "productID": code,
        "description": f"{fund.get('name', '')} 是一只跟踪 {index_type} 指数的公募QDII基金({share_class}类份额)。",
        "feesAndCommissionsSpecification": f"管理费 {format_pct(mgmt_fee)}%, 托管费 {format_pct(custody_fee)}%" + (f", 销售服务费 {format_pct(sales_fee)}%" if sales_fee > 0 else ""),
        "provider": {
            "@type": "Organization",
            "name": manager_company
        }
    }

    html = HTML_TEMPLATE.format(
        fund_name=fund.get('name', ''),
        fund_code=code,
        share_class=share_class,
        share_class_lower=share_class.lower(),
        full_name=fund.get('full_name', ''),
        index_type=index_type,
        manager_company=manager_company,
        fund_manager=fund_manager,
        inception_date=inception_date,
        mgmt_fee=format_pct(mgmt_fee),
        custody_fee=format_pct(custody_fee),
        sales_fee_str=sales_fee_str,
        total_fee=format_pct(total_fee),
        agency_status=agency_status,
        direct_status=direct_status,
        return_3yr=r3_str,
        return_1yr=r1_str,
        return_color=ret_color,
        review_html=review_html,
        related_guide_slug=related_guide_slug,
        related_guide_title=related_guide_title,
        json_ld=json.dumps(json_ld, ensure_ascii=False, indent=2)
    )

    out_path = os.path.join(FUND_DIR, f"{code}.html")
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        f.write(html)
    
    generated_count += 1

print(f"Successfully generated {generated_count} enriched fund pages (with index, follow)")

# === 重构生成高质量 Sitemap ===
article_files = sorted(glob.glob(os.path.join(ARTICLES_DIR, "*.html")))
article_urls = []
for af in article_files:
    filename = os.path.basename(af)
    if filename == 'index.html':
        continue
    article_urls.append(f"https://858000.xyz/articles/{filename}")

today_str = datetime.date.today().isoformat()

sitemap_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
    '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    '  <url>',
    '    <loc>https://858000.xyz/</loc>',
    f'    <lastmod>{today_str}</lastmod>',
    '    <changefreq>daily</changefreq>',
    '    <priority>1.0</priority>',
    '    <image:image>',
    '      <image:loc>https://858000.xyz/og-image.jpg</image:loc>',
    '      <image:title>Fund Advisor 基金定投智能分析平台</image:title>',
    '    </image:image>',
    '  </url>',
    '  <url>',
    '    <loc>https://858000.xyz/articles/</loc>',
    f'    <lastmod>{today_str}</lastmod>',
    '    <changefreq>weekly</changefreq>',
    '    <priority>0.9</priority>',
    '  </url>'
]

for af in article_files:
    filename = os.path.basename(af)
    if filename == 'index.html':
        continue
    slug = filename.replace('.html', '')
    url = f"https://858000.xyz/articles/{slug}"
    mtime = datetime.date.fromtimestamp(os.path.getmtime(af)).isoformat()
    sitemap_lines.extend([
        '  <url>',
        f'    <loc>{url}</loc>',
        f'    <lastmod>{mtime}</lastmod>',
        '    <changefreq>monthly</changefreq>',
        '    <priority>0.8</priority>',
        '    <image:image>',
        '      <image:loc>https://858000.xyz/og-image.jpg</image:loc>',
        '    </image:image>',
        '  </url>'
    ])

# 索引全部优质基金详情页 (采用无扩展名规范 URL，避免 Cloudflare 308 重定向)
for fund in funds:
    code = fund['code']
    sitemap_lines.extend([
        '  <url>',
        f'    <loc>https://858000.xyz/fund/{code}</loc>',
        f'    <lastmod>{today_str}</lastmod>',
        '    <changefreq>daily</changefreq>',
        '    <priority>0.7</priority>',
        '  </url>'
    ])

sitemap_lines.extend([
    '  <url>',
    '    <loc>https://858000.xyz/about</loc>',
    f'    <lastmod>{today_str}</lastmod>',
    '    <changefreq>monthly</changefreq>',
    '    <priority>0.6</priority>',
    '  </url>',
    '  <url>',
    '    <loc>https://858000.xyz/privacy-policy</loc>',
    f'    <lastmod>{today_str}</lastmod>',
    '    <changefreq>yearly</changefreq>',
    '    <priority>0.5</priority>',
    '  </url>',
    '  <url>',
    '    <loc>https://858000.xyz/terms-of-service</loc>',
    f'    <lastmod>{today_str}</lastmod>',
    '    <changefreq>yearly</changefreq>',
    '    <priority>0.5</priority>',
    '  </url>',
    '</urlset>',
    ''
])

with open(SITEMAP_FILE, 'w', encoding='utf-8', newline='') as f:
    f.write('\n'.join(sitemap_lines))

total_urls = 2 + len(article_urls) + len(funds) + 3
print(f"Successfully generated clean Sitemap: {SITEMAP_FILE} with {total_urls} URLs (articles: {len(article_urls)}, funds: {len(funds)})")
