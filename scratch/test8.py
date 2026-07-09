import requests, re, json, datetime

def fetch_returns(code):
    data = {}
    pz_url = f'http://fund.eastmoney.com/pingzhongdata/{code}.js'
    pz_resp = requests.get(pz_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    pz_text = pz_resp.text
    
    # 尝试读取官方 1年、3年收益率
    m1 = re.search(r'syl_1n\s*=\s*"([^"]+)"', pz_text)
    if m1 and m1.group(1): data['return_1yr'] = float(m1.group(1)) / 100
    
    m_net = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', pz_text)
    if m_net:
        nwt = json.loads(m_net.group(1))
        if nwt:
            data['inception_date'] = datetime.datetime.fromtimestamp(nwt[0]['x']/1000).strftime('%Y-%m-%d')
            data['return_since'] = nwt[-1]['equityReturn'] / 100
            
            latest_ts = nwt[-1]['x']
            latest_r = nwt[-1]['equityReturn'] / 100
            
            # 3年 = 1095天 = 94608000000 ms
            ts_3y = latest_ts - 94608000000
            if ts_3y >= nwt[0]['x']:
                pt = min(nwt, key=lambda d: abs(d['x'] - ts_3y))
                old_r = pt['equityReturn'] / 100
                data['return_3yr'] = (1 + latest_r) / (1 + old_r) - 1
            else:
                data['return_3yr'] = None

    return data

print('019547:', fetch_returns('019547'))
print('160213:', fetch_returns('160213'))
