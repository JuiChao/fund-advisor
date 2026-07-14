import requests, re
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

code = '016532'

# 1. 基金主页
resp = requests.get(f'https://fund.eastmoney.com/{code}.html', headers=HEADERS, timeout=15)
resp.encoding = 'utf-8'
text = resp.text

print("=== 基金主页可提取字段 ===")

# 基金名称
m = re.search(r'class="fundDetail-tit"[^>]*>\s*<div[^>]*>(.*?)<', text)
print(f"名称区域: {m.group(1).strip() if m else 'N/A'}")

# 基金类型
m = re.search(r'基金类型[：:]\s*</span>\s*<td[^>]*>(.*?)<', text)
if not m:
    m = re.search(r'基金类型.*?<td[^>]*>(.*?)<', text)
print(f"基金类型: {m.group(1).strip() if m else 'N/A'}")

# 基金经理
m = re.search(r'基金经理.*?<a[^>]*>(.*?)</a>', text)
print(f"基金经理: {m.group(1).strip() if m else 'N/A'}")

# 管理人/基金公司
m = re.search(r'管理人.*?<a[^>]*>(.*?)</a>', text)
print(f"管理人: {m.group(1).strip() if m else 'N/A'}")

# 托管人/托管银行
m = re.search(r'托管人.*?<a[^>]*>(.*?)</a>', text)
if not m:
    m = re.search(r'托管人.*?<td[^>]*>(.*?)<', text)
print(f"托管人: {m.group(1).strip() if m else 'N/A'}")

# 跟踪标的
m = re.search(r'跟踪标的.*?<td[^>]*>(.*?)<', text)
print(f"跟踪标的: {m.group(1).strip() if m else 'N/A'}")

# 赎回状态
m = re.search(r'赎回状态.*?>(暂停赎回|开放赎回)', text)
print(f"赎回状态: {m.group(1).strip() if m else 'N/A'}")

# 最新净值
m = re.search(r'dataOfFund.*?fund_sourceRate.*?\"(\d+\.\d+)\"', text)
if not m:
    m = re.search(r'data-fundcode.*?单位净值.*?([\d.]+)', text)
print(f"最新净值: {m.group(1) if m else 'N/A'}")

# 2. 基金详情页 f10
print("\n=== 基金详情页 (f10) ===")
resp2 = requests.get(f'https://fundf10.eastmoney.com/jbgk_{code}.html', headers=HEADERS, timeout=15)
resp2.encoding = 'utf-8'
text2 = resp2.text
soup = BeautifulSoup(text2, 'html.parser')

# 查找所有 table.info 里的信息
tables = soup.find_all('table', class_='info')
for table in tables:
    rows = table.find_all('tr')
    for row in rows:
        ths = row.find_all('th')
        tds = row.find_all('td')
        for i, th in enumerate(ths):
            td = tds[i] if i < len(tds) else None
            label = th.get_text(strip=True)
            value = td.get_text(strip=True) if td else ''
            if value:
                print(f"  {label}: {value[:80]}")

# 3. pingzhongdata 变量列表
print("\n=== pingzhongdata 可用变量 ===")
pz = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js', headers=HEADERS)
pz_text = pz.text
vars_found = re.findall(r'var\s+(\w+)\s*=', pz_text)
print(f"  变量列表: {vars_found}")

# 基金经理
m = re.search(r'var Data_currentFundManager\s*=\s*(\[.*?\]);', pz_text)
if m:
    import json
    managers = json.loads(m.group(1))
    for mgr in managers:
        print(f"  基金经理: {mgr.get('name', 'N/A')} (任职: {mgr.get('workTime', 'N/A')}, 天数: {mgr.get('power', {}).get('avr', 'N/A')})")

# fS_name
m = re.search(r'fS_name\s*=\s*"([^"]+)"', pz_text)
print(f"  fS_name: {m.group(1) if m else 'N/A'}")

print("\nDone")
