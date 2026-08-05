import json
import os
import shutil

# 路径配置
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, 'public', 'data', 'funds.json')
FUND_DIR = os.path.join(ROOT_DIR, 'public', 'fund')
SITEMAP_FILE = os.path.join(ROOT_DIR, 'public', 'sitemap.xml')

# 清理并创建 fund 目录
if os.path.exists(FUND_DIR):
    shutil.rmtree(FUND_DIR)
os.makedirs(FUND_DIR)

# 加载数据
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    funds = json.load(f)

# HTML 模板
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{fund_name} ({fund_code}) 费率_限购_历史收益 - Fund Advisor</title>
<meta name="description" content="{fund_name}({fund_code})是跟踪{index_type}指数的优质QDII基金。当前代销状态：{agency_status}，直销状态：{direct_status}。管理费{mgmt_fee}%，托管费{custody_fee}%。近3年收益率{return_3yr}%。点击查看详细定投模拟与评分排名。">
<meta name="keywords" content="{fund_code}, {fund_name}, {index_type}, 费率, 限购, 收益率, 定投, Fund Advisor">
<link rel="icon" type="image/png" href="/favicon.png">
<link rel="stylesheet" href="/css/style.css">
<script type="application/ld+json">
{json_ld}
</script>
</head>
<body>
<header>
<nav class="navbar">
    <div class="brand">
        <a href="/" style="display:flex;align-items:center;text-decoration:none;color:inherit">
            <img src="/favicon.png" alt="Fund Advisor" class="brand-logo">
            <span class="brand-text">FUND ADVISOR</span>
        </a>
    </div>
    <div class="links">
        <a href="/">返回首页</a>
    </div>
</nav>
</header>
<main class="container">
    <div class="card" style="margin-top:2rem">
        <h1 style="font-size:1.5rem;margin-bottom:0.5rem">{fund_name} (<span style="color:var(--txt2)">{fund_code}</span>)</h1>
        <p style="color:var(--txt2);margin-bottom:1.5rem">{full_name} | {manager_company} | 成立日期: {inception_date}</p>
        
        <div class="g2" style="margin-bottom:1.5rem">
            <div style="background:var(--bg2);padding:1rem;border-radius:8px">
                <div style="color:var(--txt3);font-size:0.85rem">综合费率</div>
                <div style="font-size:1.25rem;font-weight:600;color:var(--txt)">{total_fee}%/年</div>
                <div style="font-size:0.8rem;color:var(--txt3);margin-top:0.25rem">管理费 {mgmt_fee}% + 托管费 {custody_fee}%</div>
            </div>
            <div style="background:var(--bg2);padding:1rem;border-radius:8px">
                <div style="color:var(--txt3);font-size:0.85rem">代销限购状态</div>
                <div style="font-size:1.25rem;font-weight:600;color:var(--txt)">{agency_status}</div>
            </div>
            <div style="background:var(--bg2);padding:1rem;border-radius:8px">
                <div style="color:var(--txt3);font-size:0.85rem">直销限购状态</div>
                <div style="font-size:1.25rem;font-weight:600;color:var(--txt)">{direct_status}</div>
            </div>
            <div style="background:var(--bg2);padding:1rem;border-radius:8px">
                <div style="color:var(--txt3);font-size:0.85rem">近3年收益率</div>
                <div style="font-size:1.25rem;font-weight:600;color:var(--{return_color})">{return_3yr}%</div>
            </div>
        </div>

        {review_html}

        <div style="text-align:center;margin:2.5rem 0 1rem 0">
            <a href="/#ranking?q={fund_code}" class="btn btn-p" style="text-decoration:none;padding:0.75rem 2rem;font-size:1.1rem">在 Fund Advisor 完整版中进行定投模拟 ➔</a>
        </div>
    </div>
</main>
<footer style="margin-top:4rem;padding:2rem 0;border-top:1px solid var(--border);text-align:center;color:var(--txt3);font-size:0.9rem">
    <div style="margin-bottom:1rem">
        <a href="/about.html" style="color:var(--txt3);margin:0 10px;text-decoration:none">关于我们</a> |
        <a href="/privacy-policy.html" style="color:var(--txt3);margin:0 10px;text-decoration:none">隐私政策</a> |
        <a href="/terms-of-service.html" style="color:var(--txt3);margin:0 10px;text-decoration:none">服务条款</a> |
        <a href="mailto:contact@858000.xyz" style="color:var(--txt3);margin:0 10px;text-decoration:none">联系我们</a>
    </div>
    <p>© 2026 Fund Advisor. All rights reserved.</p>
</footer>
</body>
</html>
"""

def format_pct(val):
    if val is None:
        return "-"
    return f"{val * 100:.2f}"

generated_urls = []

for fund in funds:
    code = fund['code']
    total_fee = fund.get('mgmt_fee', 0) + fund.get('custody_fee', 0)
    
    r3 = fund.get('return_3yr')
    if r3 is not None:
        r3_str = format_pct(r3)
        ret_color = "ok" if r3 > 0 else "err"
    else:
        r3_str = "-"
        ret_color = "txt"

    agency_status = fund.get('limit_status', '正常')
    direct_status = fund.get('direct_limit_status') or agency_status

    json_ld = {
        "@context": "https://schema.org",
        "@type": "FinancialProduct",
        "name": fund.get('name', ''),
        "productID": code,
        "description": f"{fund.get('name', '')} 是一只跟踪 {fund.get('index_type', '')} 指数的基金。",
        "feesAndCommissionsSpecification": f"管理费 {format_pct(fund.get('mgmt_fee'))}%, 托管费 {format_pct(fund.get('custody_fee'))}%"
    }

    review_fee_desc = "在同类产品中属于中等水平"
    if total_fee <= 0.008:
        review_fee_desc = "在同类产品中处于极低水平，非常适合长期定投，能为您显著节省复利成本"
    elif total_fee >= 0.012:
        review_fee_desc = "在同类产品中偏高，建议对比其他低费率平替产品"
        
    review_status_desc = f"目前该基金的代销渠道状态为“{agency_status}”，直销渠道状态为“{direct_status}”。"
    if "暂停" in agency_status and "暂停" not in direct_status:
        review_status_desc += "如果您发现无法在天天基金或支付宝等平台买入，建议前往基金公司官网或官方APP通过直销渠道申购，通常可以突破代销限额。"
    elif "暂停" in agency_status and "暂停" in direct_status:
        review_status_desc += "由于外汇额度等原因，目前可能无法大额申购，建议关注本站的平替基金推荐。"
        
    review_return_desc = f"近三年历史收益率为 {r3_str}%。" if r3 is not None else "暂无近三年完整历史收益数据。"
    
    review_html = f"""
        <div class="fund-seo-review" style="margin-top:2rem;line-height:1.7;color:var(--txt2);font-size:1.05rem;">
            <h2 style="font-size:1.25rem;color:var(--txt);margin-bottom:1rem;font-weight:600;">{fund.get('name', '')} 深度评测</h2>
            <p style="margin-bottom:1rem;">
                <strong>{fund.get('name', '')} ({code})</strong> 是一只由{fund.get('manager_company', '')}发行的优质指数产品，主要追踪 <strong>{fund.get('index_type', '')}</strong> 指数。成立于 {fund.get('inception_date', '-')}。作为一只紧密跟踪海外核心资产的 QDII 基金，它为境内投资者提供了便捷的全球资产配置渠道。
            </p>
            <p style="margin-bottom:1rem;">
                在费率方面，该基金的综合费率为每年 <strong>{format_pct(total_fee)}%</strong>（其中管理费 {format_pct(fund.get('mgmt_fee'))}%，托管费 {format_pct(fund.get('custody_fee'))}%）。这一费率结构{review_fee_desc}。在长达数十年的定投复利过程中，费率是影响最终财富积累的核心因素之一。
            </p>
            <p style="margin-bottom:1rem;">
                {review_status_desc} QDII基金由于受国家外汇管理局的QDII额度审批限制，常常会根据额度余量调整限购政策，这是投资海外市场特有的现象。
            </p>
            <p>
                业绩方面，该基金{review_return_desc} 值得注意的是，指数基金的过往业绩主要取决于底层指数（{fund.get('index_type', '')}）的Beta收益，而不代表对未来表现的保证。如果您计划投资该基金，我们强烈建议您使用 Fund Advisor 的蒙特卡洛模拟器，测算在不同的定投预算和年限下，该基金可能呈现的风险收益分布。
            </p>
        </div>
    """

    html = HTML_TEMPLATE.format(
        fund_name=fund.get('name', ''),
        fund_code=code,
        full_name=fund.get('full_name', ''),
        index_type=fund.get('index_type', ''),
        manager_company=fund.get('manager_company', ''),
        inception_date=fund.get('inception_date', '-'),
        mgmt_fee=format_pct(fund.get('mgmt_fee')),
        custody_fee=format_pct(fund.get('custody_fee')),
        total_fee=format_pct(total_fee),
        agency_status=agency_status,
        direct_status=direct_status,
        return_3yr=r3_str,
        return_color=ret_color,
        review_html=review_html,
        json_ld=json.dumps(json_ld, ensure_ascii=False, indent=2)
    )

    out_path = os.path.join(FUND_DIR, f"{code}.html")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    generated_urls.append(f"https://858000.xyz/fund/{code}.html")

print(f"Successfully generated {len(generated_urls)} fund pages")

# === 更新 Sitemap ===
if os.path.exists(SITEMAP_FILE):
    with open(SITEMAP_FILE, 'r', encoding='utf-8') as f:
        sitemap_content = f.read()

    # 移除原有的自动生成的 <url>...</url> (我们可以在 <!-- FUNDS_START --> 和 <!-- FUNDS_END --> 之间写入)
    # 如果没有标签，我们就在 </urlset> 前插入
    
    import re
    if '<!-- FUNDS_START -->' in sitemap_content:
        sitemap_content = re.sub(r'<!-- FUNDS_START -->.*<!-- FUNDS_END -->', '', sitemap_content, flags=re.DOTALL)
    else:
        sitemap_content = sitemap_content.replace('</urlset>', '')

    # 组装新的 funds XML
    funds_xml = "<!-- FUNDS_START -->\n"
    for url in generated_urls:
        funds_xml += f"""  <url>
    <loc>{url}</loc>
    <changefreq>daily</changefreq>
    <priority>0.7</priority>
  </url>\n"""
    funds_xml += "<!-- FUNDS_END -->\n</urlset>"

    sitemap_content = sitemap_content.strip() + "\n" + funds_xml

    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)
    
    print(f"Successfully updated Sitemap: {SITEMAP_FILE}")

