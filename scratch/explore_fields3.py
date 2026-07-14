import requests, re, json
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

code = '016532'

# f10 基本概况页
resp = requests.get(f'https://fundf10.eastmoney.com/jbgk_{code}.html', headers=HEADERS, timeout=15)
resp.encoding = 'utf-8'
soup = BeautifulSoup(resp.text, 'html.parser')

fields = {}
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
            # 也保存链接文本
            links = td.find_all('a') if td else []
            link_texts = [a.get_text(strip=True) for a in links]
            fields[label] = {'text': value, 'links': link_texts}

# 写入文件避免编码问题
with open('scratch/fields_016532.json', 'w', encoding='utf-8') as f:
    json.dump(fields, f, ensure_ascii=False, indent=2)

print("Done - see scratch/fields_016532.json")
