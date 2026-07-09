import requests, re

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# 检查易方达、天弘、博时等基金的实际申购状态
funds_to_check = [
    ('016532', '易方达纳斯达克100'),
    ('016055', '博时纳斯达克100'),
    ('018043', '天弘纳斯达克100'),
    ('160213', '国泰纳斯达克100LOF'),
    ('040046', '华安纳斯达克100'),
    ('000834', '大成纳斯达克100'),
    ('161130', '易方达纳斯达克100联接'),
    ('270042', '广发纳斯达克100联接'),
    ('539001', '建信纳斯达克100'),
    ('019547', '招商纳斯达克100'),
    ('050025', '博时标普500联接'),
    ('007721', '天弘标普500'),
    ('013425', '华宝标普500'),
]

for code, name in funds_to_check:
    resp = requests.get(f'https://fund.eastmoney.com/{code}.html', headers=HEADERS, timeout=15)
    resp.encoding = 'utf-8'
    text = resp.text
    
    has_pause = '暂停申购' in text
    has_pause_large = '暂停大额申购' in text
    has_limit_purchase = '限大额' in text
    
    # 检查具体的申购状态文本
    # 通常在 class="fundDetail-tit" 或特定区域
    status_match = re.search(r'申购状态[^<]*?<[^>]*>([^<]+)', text)
    status_text = status_match.group(1).strip() if status_match else 'N/A'
    
    # 检查购买按钮区域
    buy_btn = re.search(r'class="[^"]*buyFund[^"]*"[^>]*>([^<]+)', text)
    buy_text = buy_btn.group(1).strip() if buy_btn else 'N/A'
    
    # 限额
    limit_match = re.search(r'单日累计购买上限\s*(\d+(?:\.\d+)?)\s*元', text) or re.search(r'购买上限.*?(\d+(?:\.\d+)?)\s*元', text)
    limit_val = limit_match.group(1) if limit_match else 'N/A'
    
    # 更精确：查找申购状态的关键区域
    sg_status = re.search(r'申购状态.*?>(暂停申购|限大额|开放申购)', text)
    sg_text = sg_status.group(1) if sg_status else 'N/A'
    
    with open('scratch/limit_debug.txt', 'a', encoding='utf-8') as f:
        f.write(f"{code} {name:20s} | 暂停申购={has_pause} | 暂停大额={has_pause_large} | 限大额={has_limit_purchase} | 申购状态={sg_text} | limit={limit_val} | buy_btn={buy_text}\n")

print("Done - see scratch/limit_debug.txt")
