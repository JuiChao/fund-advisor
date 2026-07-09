import requests, re

def check_limit(code):
    resp = requests.get(f'https://fund.eastmoney.com/{code}.html', headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    resp.encoding = 'utf-8'
    text = resp.text
    
    has_pause = '暂停申购' in text
    has_pause_large = '暂停大额申购' in text
    limit_match = re.search(r'单日累计购买上限\s*(\d+(?:\.\d+)?)\s*元', text) or re.search(r'购买上限.*?(\d+(?:\.\d+)?)\s*元', text)
    limit_val = limit_match.group(1) if limit_match else None
    min_buy = re.search(r'fund_minsg="([^"]+)"', text)
    min_buy_val = min_buy.group(1) if min_buy else None

    # Check the actual purchase status from the JS API
    pz_text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    fund_minsg = re.search(r'fund_minsg="([^"]+)"', pz_text)
    ishb = re.search(r'ishb\s*=\s*(true|false)', pz_text)
    
    print(f"{code}: pause={has_pause}, pause_large={has_pause_large}, limit={limit_val}, minsg_html={min_buy_val}, minsg_js={fund_minsg.group(1) if fund_minsg else None}, ishb={ishb.group(1) if ishb else None}")

for code in ['019547', '013425', '016532', '040046', '019441']:
    check_limit(code)
