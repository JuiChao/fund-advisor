import requests, json, re, datetime

def debug_data(code):
    text = requests.get(f'http://fund.eastmoney.com/pingzhongdata/{code}.js').text
    
    # Check Data_netWorthTrend (full history)
    m_nwt = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text)
    nwt = json.loads(m_nwt.group(1)) if m_nwt else []
    
    # Check Data_grandTotal (cumulative return)
    m_gt = re.search(r'var Data_grandTotal\s*=\s*(\[.*?\]);', text)
    gt_raw = json.loads(m_gt.group(1)) if m_gt else []
    gt = gt_raw[0]['data'] if gt_raw else []
    
    nwt_start = datetime.datetime.fromtimestamp(nwt[0]['x']/1000, tz=datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d') if nwt else 'N/A'
    gt_start = datetime.datetime.fromtimestamp(gt[0][0]/1000, tz=datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d') if gt else 'N/A'
    
    print(f"{code}:")
    print(f"  NWT: {len(nwt)} points, from {nwt_start}, first_y={nwt[0]['y'] if nwt else 'N/A'}, last_y={nwt[-1]['y'] if nwt else 'N/A'}")
    print(f"  GT:  {len(gt)} points, from {gt_start}, first_val={gt[0][1] if gt else 'N/A'}, last_val={gt[-1][1] if gt else 'N/A'}")
    
    # The CORRECT way: use NAV (net asset value) from NWT to compute returns
    if nwt:
        first_nav = nwt[0]['y']
        last_nav = nwt[-1]['y']
        since_return = (last_nav / first_nav - 1)
        print(f"  Since inception: NAV {first_nav} -> {last_nav}, return = {since_return*100:.2f}%")
        
        # 3yr return
        latest_ts = nwt[-1]['x']
        ts_3y = latest_ts - int(3 * 365.25 * 24 * 3600 * 1000)
        if ts_3y >= nwt[0]['x']:
            pt_3y = min(nwt, key=lambda d: abs(d['x'] - ts_3y))
            nav_3y = pt_3y['y']
            r3 = (last_nav / nav_3y - 1)
            print(f"  3yr return: NAV {nav_3y} -> {last_nav}, return = {r3*100:.2f}%")
        else:
            print(f"  3yr return: N/A (fund is younger than 3 years)")
    
    # Check syl values
    for var in re.findall(r'(syl_[a-zA-Z0-9]+)="([^"]*)"', text):
        print(f"  {var[0]} = {var[1]}%")

for code in ['016532', '160213', '040046', '019547', '050025', '096001']:
    debug_data(code)
    print()
