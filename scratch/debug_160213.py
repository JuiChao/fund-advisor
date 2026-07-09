import requests, json, re, datetime

text = requests.get('http://fund.eastmoney.com/pingzhongdata/160213.js').text
m = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text)
nwt = json.loads(m.group(1))

last_nav = nwt[-1]['y']
latest_ts = nwt[-1]['x']

# Find 1yr ago
ts_1y = latest_ts - int(365.25 * 24 * 3600 * 1000)
pt_1y = min(nwt, key=lambda d: abs(d['x'] - ts_1y))

dt_1y = datetime.datetime.fromtimestamp(pt_1y['x']/1000, tz=datetime.timezone(datetime.timedelta(hours=8)))
dt_last = datetime.datetime.fromtimestamp(latest_ts/1000, tz=datetime.timezone(datetime.timedelta(hours=8)))

print(f"160213 (LOF):")
print(f"  Latest: date={dt_last.strftime('%Y-%m-%d')}, NAV={last_nav}")
print(f"  1yr ago: date={dt_1y.strftime('%Y-%m-%d')}, NAV={pt_1y['y']}")
print(f"  1yr return: {(last_nav / pt_1y['y'] - 1)*100:.2f}%")
print(f"  Total points: {len(nwt)}")

# Check if this is a LOF with different NAV structure
# Let's look at the NAV around 1 year ago more carefully
print(f"\n  NAVs around 1yr ago:")
for p in nwt:
    if abs(p['x'] - ts_1y) < 7 * 24 * 3600 * 1000:  # within 7 days
        d = datetime.datetime.fromtimestamp(p['x']/1000, tz=datetime.timezone(datetime.timedelta(hours=8)))
        print(f"    {d.strftime('%Y-%m-%d')}: NAV={p['y']}")

# syl_1n should be the true 1yr return
m1 = re.search(r'syl_1n\s*=\s*"([^"]*)"', text)
print(f"\n  syl_1n (official 1yr): {m1.group(1)}%" if m1 else "  syl_1n: N/A")

# It's a LOF - it likely had a large split/dividend
# Let's check Data_ACWorthTrend (累计净值) instead
m_ac = re.search(r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', text)
if m_ac:
    act = json.loads(m_ac.group(1))
    last_ac = act[-1]
    pt_1y_ac = min(act, key=lambda d: abs(d[0] - ts_1y))
    dt_1y_ac = datetime.datetime.fromtimestamp(pt_1y_ac[0]/1000, tz=datetime.timezone(datetime.timedelta(hours=8)))
    print(f"\n  ACWorth (累计净值):")
    print(f"    Latest: NAV={last_ac[1]}")
    print(f"    1yr ago ({dt_1y_ac.strftime('%Y-%m-%d')}): NAV={pt_1y_ac[1]}")
    print(f"    1yr return: {(last_ac[1] / pt_1y_ac[1] - 1)*100:.2f}%")
