import requests, json, re, datetime

tz8 = datetime.timezone(datetime.timedelta(hours=8))

def test_fund(code):
    text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    
    # Data_ACWorthTrend = 累计净值走势 (accounts for dividends/splits)
    m_ac = re.search(r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', text)
    # Data_netWorthTrend = 单位净值走势
    m_nwt = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text)
    
    if m_ac:
        act = json.loads(m_ac.group(1))
        if act:
            first = act[0]
            last = act[-1]
            inception = datetime.datetime.fromtimestamp(first[0]/1000, tz=tz8).strftime('%Y-%m-%d')
            since_return = (last[1] / first[1] - 1)
            
            latest_ts = last[0]
            
            # 1yr
            ts_1y = latest_ts - int(365.25 * 24 * 3600 * 1000)
            if ts_1y >= first[0]:
                pt = min(act, key=lambda d: abs(d[0] - ts_1y))
                r1 = (last[1] / pt[1] - 1)
            else:
                r1 = since_return
                
            # 3yr 
            ts_3y = latest_ts - int(3 * 365.25 * 24 * 3600 * 1000)
            if ts_3y >= first[0]:
                pt = min(act, key=lambda d: abs(d[0] - ts_3y))
                r3 = (last[1] / pt[1] - 1)
            else:
                r3 = None
            
            r1s = f"{r1*100:.2f}%"
            r3s = f"{r3*100:.2f}%" if r3 is not None else "N/A"
            rss = f"{since_return*100:.2f}%"
            print(f"{code} | inception={inception} | 1yr={r1s:10s} | 3yr={r3s:10s} | since={rss}")
    
    # Check syl_1n for comparison
    m1 = re.search(r'syl_1n\s*=\s*"([^"]*)"', text)
    if m1: print(f"       syl_1n(official)={m1.group(1)}%")

for code in ['160213', '016532', '040046', '019547', '050025', '096001']:
    test_fund(code)
    print()
