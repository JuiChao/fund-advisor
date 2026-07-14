import requests, re, json
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

codes = ['016532', '040046', '050025']

for code in codes:
    print(f"\n{'='*60}")
    print(f"基金 {code}")
    print(f"{'='*60}")

    # f10 基本概况页
    resp = requests.get(f'https://fundf10.eastmoney.com/jbgk_{code}.html', headers=HEADERS, timeout=15)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    tables = soup.find_all('table', class_='info')
    fields = {}
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
                    fields[label] = value
    
    print("  === f10 基本概况 ===")
    for k, v in fields.items():
        print(f"  {k}: {v[:100]}")
    
    # pingzhongdata - 基金经理
    pz = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js', headers=HEADERS)
    pz_text = pz.text
    
    # 基金经理（用更宽松的解析）
    m = re.search(r'var Data_currentFundManager\s*=\s*(\[.*?\])\s*;', pz_text, re.DOTALL)
    if m:
        try:
            # 有时候有多层嵌套，截取到第一个 ]; 即可
            raw = m.group(1)
            # 尝试修复可能的JSON问题
            managers = json.loads(raw)
            for mgr in managers:
                print(f"  基金经理详情: 姓名={mgr.get('name')}, 任职日期={mgr.get('workTime')}")
        except:
            # 手工提取
            names = re.findall(r'"name":"([^"]+)"', raw)
            work_times = re.findall(r'"workTime":"([^"]+)"', raw)
            for i, name in enumerate(names):
                wt = work_times[i] if i < len(work_times) else 'N/A'
                print(f"  基金经理(regex): 姓名={name}, 任职日期={wt}")

    # 基金主页 - 基金经理
    resp2 = requests.get(f'https://fund.eastmoney.com/{code}.html', headers=HEADERS, timeout=15)
    resp2.encoding = 'utf-8'
    text2 = resp2.text
    
    mgr_match = re.search(r'基金经理.*?<a[^>]*>(.*?)</a>', text2)
    print(f"  基金经理(主页): {mgr_match.group(1) if mgr_match else 'N/A'}")
    
    # 最新净值
    m = re.search(r'fund_sourceRate\s*=\s*"([^"]*)"', pz_text)
    print(f"  原费率: {m.group(1) if m else 'N/A'}")
    m = re.search(r'fund_Rate\s*=\s*"([^"]*)"', pz_text)
    print(f"  优惠费率: {m.group(1) if m else 'N/A'}")

print("\nDone")
