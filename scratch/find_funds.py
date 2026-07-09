import re
import json
import requests

def main():
    print("Downloading fund list from EastMoney...")
    url = "http://fund.eastmoney.com/js/fundcode_search.js"
    resp = requests.get(url)
    resp.encoding = 'utf-8'
    text = resp.text
    
    # Extract the array
    match = re.search(r'var r = (\[.*\]);', text)
    if not match:
        print("Failed to parse")
        return
        
    funds = json.loads(match.group(1))
    
    nasdaq_a = []
    sp500_a = []
    
    for fund in funds:
        code = fund[0]
        name = fund[2]
        
        # We want index/QDII funds, typically A class
        if "纳斯达克" in name or "纳指" in name:
            if "100" in name and name.endswith("A") and "美元" not in name:
                nasdaq_a.append((code, name))
        if "标普500" in name:
            if name.endswith("A") and "美元" not in name:
                sp500_a.append((code, name))
                
    with open("scratch/funds_list.txt", "w", encoding="utf-8") as f:
        f.write(f"Found {len(nasdaq_a)} Nasdaq 100 Class A funds:\n")
        for c, n in nasdaq_a:
            f.write(f"  ('{c}', '纳斯达克100'), # {n}\n")
            
        f.write(f"\nFound {len(sp500_a)} S&P 500 Class A funds:\n")
        for c, n in sp500_a:
            f.write(f"  ('{c}', '标普500'), # {n}\n")
            
    print("Done")

if __name__ == '__main__':
    main()
