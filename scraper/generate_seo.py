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

        <div style="text-align:center;margin:2.5rem 0 1rem 0">
            <a href="/#ranking?q={fund_code}" class="btn btn-p" style="text-decoration:none;padding:0.75rem 2rem;font-size:1.1rem">在 Fund Advisor 完整版中进行定投模拟 ➔</a>
        </div>
    </div>
</main>
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

