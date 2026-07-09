import requests, json, re

# Check what equityReturn actually contains
text = requests.get('http://fund.eastmoney.com/pingzhongdata/016532.js').text
m = re.search(r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text)
nwt = json.loads(m.group(1))

print(f"Total points: {len(nwt)}")
print(f"First point: {nwt[0]}")
print(f"Last point: {nwt[-1]}")
print(f"Last equityReturn raw value: {nwt[-1]['equityReturn']}")
print(f"If divided by 100: {nwt[-1]['equityReturn'] / 100}")
print()

# Check syl values
m1 = re.search(r'syl_1n\s*=\s*"([^"]+)"', text)
print(f"syl_1n (1yr return %): {m1.group(1) if m1 else 'N/A'}")

# What does the syl_1n value mean? It's already a percentage like "20.68"
# And equityReturn is also already a percentage like 0.29
# So equityReturn is NOT a percentage to be divided by 100!
# equityReturn values are already in decimal form (0.29 means 0.29%, not 29%)

# Let's verify: check the Data_grandTotal
m2 = re.search(r'var Data_grandTotal\s*=\s*(\[.*?\]);', text)
gt = json.loads(m2.group(1))
print(f"\nData_grandTotal last point: {gt[0]['data'][-1]}")
print(f"Data_grandTotal means: {gt[0]['data'][-1][1]}% cumulative return")

# Now check a few equityReturn values 
print(f"\nSample equityReturn values from last 5 days:")
for pt in nwt[-5:]:
    print(f"  {pt['x']}: equityReturn={pt['equityReturn']}")
