import requests, re

def test_returns(code):
    resp = requests.get(f'http://fund.eastmoney.com/{code}.html', headers={'User-Agent': 'Mozilla/5.0'})
    resp.encoding = 'utf-8'
    text = resp.text
    
    m1 = re.search(r'<td[^>]*>近1年[^<]*</td>\s*<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%', text)
    m3 = re.search(r'<td[^>]*>近3年[^<]*</td>\s*<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%', text)
    ms = re.search(r'<td[^>]*>成立来[^<]*</td>\s*<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%', text)
    
    print(f"{code}: 1y={m1.group(1) if m1 else None}, 3y={m3.group(1) if m3 else None}, since={ms.group(1) if ms else None}")

test_returns('019547')
test_returns('160213')
