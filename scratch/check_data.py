import json

data = json.load(open('public/data/funds.json', encoding='utf-8'))
for d in data:
    code = d.get('code', '?')
    name = d.get('name', '?')[:20]
    r1 = d.get('return_1yr')
    r3 = d.get('return_3yr')
    rs = d.get('return_since')
    ls = d.get('limit_status', '?')
    inc = d.get('inception_date', '?')
    dl = d.get('daily_limit')
    r1s = f"{r1*100:.2f}%" if r1 is not None else "N/A"
    r3s = f"{r3*100:.2f}%" if r3 is not None else "N/A"
    rss = f"{rs*100:.2f}%" if rs is not None else "N/A"
    print(f"{code} | {name:20s} | 1yr={r1s:10s} | 3yr={r3s:10s} | since={rss:10s} | limit={str(ls):12s} dl={str(dl):6s} | inception={inc}")
