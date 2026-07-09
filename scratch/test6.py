import requests
import re
resp = requests.get('http://fund.eastmoney.com/019547.html', headers={'User-Agent': 'Mozilla/5.0'})
resp.encoding='utf-8'
text = resp.text

m1 = re.search(r'近1年.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)
m3 = re.search(r'近3年.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)
m_since = re.search(r'成立来.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)

print("019547:")
print("1yr:", m1.group(1) if m1 else None)
print("3yr:", m3.group(1) if m3 else None)
print("since:", m_since.group(1) if m_since else None)

resp = requests.get('http://fund.eastmoney.com/160213.html', headers={'User-Agent': 'Mozilla/5.0'})
resp.encoding='utf-8'
text = resp.text

m1 = re.search(r'近1年.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)
m3 = re.search(r'近3年.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)
m_since = re.search(r'成立来.*?<td[^>]*>(?:<div[^>]*>)?(?:<span[^>]*>)?(-?\d+\.\d+)%(?:</span>)?(?:</div>)?</td>', text)

print("\n160213:")
print("1yr:", m1.group(1) if m1 else None)
print("3yr:", m3.group(1) if m3 else None)
print("since:", m_since.group(1) if m_since else None)
