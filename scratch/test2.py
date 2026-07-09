import requests
import re
text = requests.get('http://fund.eastmoney.com/pingzhongdata/019547.js').text
for var in re.findall(r'(syl_[a-z0-9]+)="([^"]+)"', text):
    print(var)
