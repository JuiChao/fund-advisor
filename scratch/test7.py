import requests
import json
import re

def get_returns(code):
    text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    
    # 1. return_1yr from syl_1n
    m1 = re.search(r'syl_1n\s*=\s*"([^"]+)"', text)
    r1 = float(m1.group(1))/100 if m1 and m1.group(1) else None
    
    # 2. Data_grandTotal for since inception and dates
    m2 = re.search(r'var Data_grandTotal\s*=\s*(\[.*?\]);', text)
    r3 = None
    rsince = None
    inception_date = None
    
    if m2:
        try:
            gt = json.loads(m2.group(1))
            if gt and len(gt) > 0:
                data = gt[0]['data']
                if data and len(data) > 0:
                    rsince = data[-1][1] / 100
                    inception_ts = data[0][0]
                    from datetime import datetime
                    inception_date = datetime.fromtimestamp(inception_ts/1000).strftime('%Y-%m-%d')
                    
                    # Calculate 3yr return if it exists
                    # 3 years = roughly 3 * 365.25 days = 1095 days
                    latest_ts = data[-1][0]
                    target_ts = latest_ts - 1095 * 24 * 3600 * 1000
                    if target_ts >= inception_ts:
                        # find the closest date
                        closest_point = min(data, key=lambda x: abs(x[0] - target_ts))
                        # cumulative return formula: (1 + r_now) / (1 + r_3yr_ago) - 1
                        r3 = ((1 + rsince) / (1 + closest_point[1]/100)) - 1
        except Exception as e:
            pass
            
    return {'return_1yr': r1, 'return_3yr': r3, 'return_since': rsince, 'inception_date': inception_date}

print('019547:', get_returns('019547'))
print('160213:', get_returns('160213'))
