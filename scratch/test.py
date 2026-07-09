import requests
import re
text = requests.get('http://fund.eastmoney.com/pingzhongdata/160213.js').text
print('1yr:', re.findall(r'syl_1n="([^"]*)"', text))
print('3yr:', re.findall(r'syl_3n="([^"]*)"', text))
