import requests, json, re, datetime

def get_correct_returns(code):
    text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    result = {}
    
    # 1yr from syl_1n (already percentage)
    m1 = re.search(r'syl_1n\s*=\s*"([^"]+)"', text)
    if m1 and m1.group(1):
        result['return_1yr'] = float(m1.group(1)) / 100  # 20.68 -> 0.2068
    
    # Cumulative returns from Data_grandTotal
    m_gt = re.search(r'var Data_grandTotal\s*=\s*(\[.*?\]);', text)
    if m_gt:
        gt = json.loads(m_gt.group(1))
        if gt and len(gt) > 0:
            data = gt[0]['data']
            if data:
                # inception date from first data point
                inception_ts = data[0][0]
                result['inception_date'] = datetime.datetime.fromtimestamp(inception_ts/1000, tz=datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d')
                
                # since inception cumulative return (already percentage)
                result['return_since'] = data[-1][1] / 100  # 11.43 -> 0.1143
                
                # 3yr return: find point ~3 years ago
                latest_ts = data[-1][0]
                ts_3y = latest_ts - 3 * 365.25 * 24 * 3600 * 1000
                
                if ts_3y >= inception_ts:
                    # Find closest point to 3 years ago
                    pt_3y = min(data, key=lambda d: abs(d[0] - ts_3y))
                    old_cum = pt_3y[1] / 100  # cumulative return 3yrs ago as decimal
                    new_cum = data[-1][1] / 100  # current cumulative return as decimal
                    # 3yr return = (1 + new_cum) / (1 + old_cum) - 1
                    result['return_3yr'] = (1 + new_cum) / (1 + old_cum) - 1
                else:
                    result['return_3yr'] = None
    
    return result

# Test with several funds
for code in ['016532', '160213', '040046', '019547', '050025']:
    r = get_correct_returns(code)
    r1 = f"{r.get('return_1yr',0)*100:.2f}%" if r.get('return_1yr') is not None else 'N/A'
    r3 = f"{r.get('return_3yr',0)*100:.2f}%" if r.get('return_3yr') is not None else 'N/A'
    rs = f"{r.get('return_since',0)*100:.2f}%" if r.get('return_since') is not None else 'N/A'
    inc = r.get('inception_date', '?')
    print(f"{code}: 1yr={r1:10s} 3yr={r3:10s} since={rs:10s} inception={inc}")
