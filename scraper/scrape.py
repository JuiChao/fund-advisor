#!/usr/bin/env python3
"""
基金数据抓取脚本
从天天基金网抓取最新数据，生成 public/data/funds.json
用法: python scraper/scrape.py
"""
import re
import json
import time
import sys
import os
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://fund.eastmoney.com/',
}
DELAY = 4  # 每只基金间隔秒数

# 兜底数据文件路径
FALLBACK = os.path.join(os.path.dirname(__file__), '..', 'data', 'funds_fallback.json')
# 输出路径
OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'funds.json')

FUND_LIST = [
    # (code, index_type)
    ('016532', '纳斯达克100'), ('016055', '纳斯达克100'), ('018043', '纳斯达克100'),
    ('160213', '纳斯达克100'), ('040046', '纳斯达克100'), ('000834', '纳斯达克100'),
    ('161130', '纳斯达克100'), ('270042', '纳斯达克100'), ('016452', '纳斯达克100'),
    ('539001', '纳斯达克100'), ('019547', '纳斯达克100'), ('018966', '纳斯达克100'),
    ('015299', '纳斯达克100'), ('019172', '纳斯达克100'), ('019441', '纳斯达克100'),
    ('019524', '纳斯达克100'),
    ('050025', '标普500'), ('161125', '标普500'), ('017641', '标普500'),
    ('017028', '标普500'), ('018064', '标普500'), ('096001', '标普500'),
    ('007721', '标普500'), ('013425', '标普500'),
]


def load_fallback():
    """加载兜底数据"""
    with open(FALLBACK, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['code']: item for item in data}


def scrape_fund_page(code):
    """从基金主页抓取"""
    url = f'https://fund.eastmoney.com/{code}.html'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        text = resp.text
        data = {}

        m = re.search(r'年化跟踪误差.*?(\d+\.\d+)%', text)
        if m: data['tracking_error'] = float(m.group(1)) / 100

        m = re.search(r'规模.*?(\d+\.\d+)\s*亿元', text)
        if m: data['scale'] = float(m.group(1))

        # 支持正负数收益率
        m = re.search(r'近1年.*?(-?\d+\.\d+)%', text)
        if m: data['return_1yr'] = float(m.group(1)) / 100

        m = re.search(r'近3年.*?(-?\d+\.\d+)%', text)
        if m: data['return_3yr'] = float(m.group(1)) / 100

        # 晨星评级：通过 class="jjpjX" 精准提取（X为1-5）
        m = re.search(r'jjpj(\d)', text)
        if m:
            data['morningstar'] = int(m.group(1))
        else:
            data['morningstar'] = 0

        # 限额限购解析
        limit_match = re.search(r'单日累计购买上限\s*(\d+(?:\.\d+)?)\s*元', text) or re.search(r'购买上限.*?(\d+(?:\.\d+)?)\s*元', text)
        if limit_match:
            dl = int(float(limit_match.group(1)))
            data['daily_limit'] = dl
            if '暂停申购' in text:
                data['limit_status'] = f'暂停(限{dl})'
            else:
                data['limit_status'] = f'限{dl}元/日'
        elif '暂停申购' in text:
            data['daily_limit'] = 0
            data['limit_status'] = '暂停申购'
        else:
            data['daily_limit'] = None
            data['limit_status'] = '正常'

        return data
    except Exception as e:
        print(f'  [WARN] 抓取 {code} 主页失败: {e}')
        return {}


def scrape_fee_page(code):
    """从费率详情页抓取"""
    url = f'https://fundf10.eastmoney.com/jjfl_{code}.html'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'utf-8'
        text = resp.text
        data = {}

        m = re.search(r'管理费率.*?(\d+\.\d+)%', text)
        if m: data['mgmt_fee'] = float(m.group(1)) / 100

        m = re.search(r'托管费率.*?(\d+\.\d+)%', text)
        if m: data['custody_fee'] = float(m.group(1)) / 100

        return data
    except Exception as e:
        print(f'  [WARN] 抓取 {code} 费率页失败: {e}')
        return {}


def validate(data):
    """校验数据"""
    checks = {
        'tracking_error': (0.001, 0.15), 'scale': (0.01, 1000),
        'return_1yr': (-0.5, 2.0), 'return_3yr': (-0.8, 5.0),
        'mgmt_fee': (0.001, 0.03), 'custody_fee': (0.0005, 0.01),
        'morningstar': (0, 5),
    }
    cleaned = {}
    for k, v in data.items():
        if k in checks:
            lo, hi = checks[k]
            if v is not None and lo <= v <= hi:
                cleaned[k] = v
            else:
                print(f'  [校验] {k}={v} 超范围，已丢弃')
        else:
            cleaned[k] = v
    return cleaned


def main():
    print('=' * 60)
    print('基金数据抓取开始')
    print('=' * 60)

    fallback = load_fallback()
    results = []
    updated = 0
    errors = []

    for code, index_type in FUND_LIST:
        print(f'\n[{code}] 抓取中...')

        # 基础数据来自兜底
        base = fallback.get(code, {})
        base['code'] = code
        base['index_type'] = index_type

        # 抓取最新数据
        page_data = scrape_fund_page(code)
        time.sleep(DELAY)
        fee_data = scrape_fee_page(code)
        time.sleep(DELAY)

        # 合并：抓取到的数据覆盖兜底数据
        merged = {**base, **page_data, **fee_data}
        merged = validate(merged)

        if page_data or fee_data:
            updated += 1
            print(f'  [OK] 更新了 {len(page_data) + len(fee_data)} 个字段')
        else:
            errors.append(f'{code}: 未获取到新数据，使用兜底数据')
            print(f'  [INFO] 使用兜底数据')

        # 确保有 name 字段
        if 'name' not in merged:
            merged['name'] = base.get('name', f'基金{code}')

        results.append(merged)

    # 输出时间戳（强制使用北京时间 UTC+8）
    from datetime import datetime, timezone, timedelta
    tz_beijing = timezone(timedelta(hours=8))
    timestamp = datetime.now(tz_beijing).strftime('%Y-%m-%dT%H:%M:%S')
    for r in results:
        r['updated_at'] = timestamp

    # 写入 JSON
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'\n{"=" * 60}')
    print(f'抓取完成: {updated}/{len(FUND_LIST)} 只基金更新')
    print(f'输出: {OUTPUT}')
    if errors:
        print(f'警告: {len(errors)} 个问题')
        for e in errors:
            print(f'  - {e}')
    print('=' * 60)

    return 0 if updated > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
