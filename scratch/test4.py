import requests
from bs4 import BeautifulSoup
import re

for code in ['019547', '160213']:
    print(f"\n--- {code} ---")
    url = f'https://fund.eastmoney.com/{code}.html'
    h = {'User-Agent': 'Mozilla/5.0'}
    text = requests.get(url, headers=h).text
    soup = BeautifulSoup(text, 'html.parser')
    
    # 成立日期 is usually in a td with class 'td01' or similar, but the easiest way is to search text
    date_match = re.search(r'成\s*立\s*日\s*[：:]\s*(?:<[^>]+>)?(\d{4}-\d{2}-\d{2})', text)
    if date_match: print('Inception Date:', date_match.group(1))
    
    stage_li = soup.find('li', id='increaseAmount_stage')
    if stage_li:
        for tr in stage_li.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) > 1:
                title = tds[0].text.strip()
                val = tds[1].text.strip()
                if title in ['近1年', '近3年', '成立来']:
                    print(f"{title}: {val}")
