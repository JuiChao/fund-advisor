import json

d = json.load(open('public/data/funds.json', encoding='utf-8'))
f = d[0]  # first fund

print(f"总基金数: {len(d)}")
print(f"\n=== 第一只基金 {f['code']} 所有字段 ===")
for k, v in f.items():
    val = str(v)[:80] if v is not None else 'None'
    print(f"  {k}: {val}")

print(f"\n=== 新增字段统计 ===")
new_fields = ['full_name', 'fund_type', 'manager_company', 'custodian', 'fund_manager',
              'benchmark', 'tracking_index', 'dividend_info', 'purchase_fee', 'sales_fee', 'issue_date']
for field in new_fields:
    count = sum(1 for f in d if f.get(field))
    print(f"  {field}: {count}/{len(d)} 只基金有数据")
