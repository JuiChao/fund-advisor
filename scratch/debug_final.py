import requests, json, re, datetime

tz8 = datetime.timezone(datetime.timedelta(hours=8))

def test_fund(code):
    text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    
    # Official syl values
    m1 = re.search(r'syl_1n\s*=\s*"([^"]*)"', text)
    r1_official = m1.group(1) if m1 else 'N/A'
    
    # ACWorthTrend for 3yr and since
    m_ac = re.search(r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', text)
    m_nwt = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text)
    
    if m_ac and m_nwt:
        act = json.loads(m_ac.group(1))
        nwt = json.loads(m_nwt.group(1))  # for inception date
        
        inception = datetime.datetime.fromtimestamp(nwt[0]['x']/1000, tz=tz8).strftime('%Y-%m-%d')
        
        last = act[-1]
        first = act[0]
        latest_ts = last[0]
        inception_ts = first[0]
        
        since_r = (last[1] / first[1] - 1)
        
        ts_3y = latest_ts - int(3 * 365.25 * 24 * 3600 * 1000)
        if ts_3y >= inception_ts:
            pt = min(act, key=lambda d: abs(d[0] - ts_3y))
            r3 = (last[1] / pt[1] - 1)
            r3s = f"{r3*100:.2f}%"
        else:
            r3 = None
            r3s = "N/A"
        
        print(f"{code} | inception={inception} | 1yr(official)={r1_official:6s}% | 3yr(ACW)={r3s:10s} | since(ACW)={since_r*100:.2f}%")

for code in ['016532', '016055', '018043', '160213', '040046', '000834', '161130', '270042', 
             '016452', '539001', '019547', '018966', '015299', '019172', '019441', '019524', '019736',
             '050025', '161125', '017641', '017028', '018064', '096001', '007721', '013425']:
    test_fund(code)
