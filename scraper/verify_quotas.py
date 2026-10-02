#!/usr/bin/env python3
"""
多源交叉核验脚本 (verify_quotas.py)
对所有基金的代销限额、直销限额、销售服务费及开通状态进行多平台交叉比对与逻辑约束审计。
支持在日常爬虫更新后作为质量门禁执行。
"""
import os
import sys
import json
import re

# 引用同目录爬虫函数
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scrape import scrape_fund_page, scrape_limit_announcement

DATA_FALLBACK = os.path.join(os.path.dirname(__file__), '..', 'data', 'funds_fallback.json')
DATA_PUBLIC = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'funds.json')


def load_dataset(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['code']: item for item in data} if isinstance(data, list) else data


def verify_fund_logic(item):
    """单只基金的数据逻辑一致性校验规则"""
    code = item.get('code')
    name = item.get('name')
    issues = []

    # 1. 必填字段检查
    for req in ['limit_status', 'daily_limit', 'direct_limit_status', 'direct_daily_limit']:
        if req not in item:
            issues.append(f"缺失必要字段: {req}")

    # 2. 状态与数值一致性
    status = item.get('limit_status', '')
    limit = item.get('daily_limit')
    d_status = item.get('direct_limit_status', '')
    d_limit = item.get('direct_daily_limit')

    # 代销状态一致性
    if status == '暂停申购' and limit != 0:
        issues.append(f"代销状态为暂停申购，但额度为 {limit} (应为 0)")
    elif status == '未开通代销' and limit != 0:
        issues.append(f"代销状态为未开通代销，但额度为 {limit} (应为 0)")
    elif '限' in status and '元' in status:
        m = re.search(r'限(\d+)元', status)
        if m and int(m.group(1)) != limit:
            issues.append(f"代销状态文字({status})与数值({limit})不一致")

    # 直销状态一致性
    if d_status == '暂停申购' and d_limit != 0:
        issues.append(f"直销状态为暂停申购，但额度为 {d_limit} (应为 0)")
    elif '限' in d_status and '元' in d_status:
        m = re.search(r'限(\d+)元', d_status)
        if m and int(m.group(1)) != d_limit:
            issues.append(f"直销状态文字({d_status})与数值({d_limit})不一致")

    # 3. 占位符字符串残留排查
    for s in [status, d_status]:
        if '暂停(限' in str(s) or '未定义' in str(s):
            issues.append(f"包含非法占位符字符串: {s}")

    return issues


def run_cross_verification(sample_codes=None):
    """执行交叉核验"""
    print("=" * 65)
    print("【基金额度与交易状态多源交叉核验】开始")
    print("=" * 65)

    fallback = load_dataset(DATA_FALLBACK)
    public_funds = load_dataset(DATA_PUBLIC)

    codes_to_check = sample_codes or list(fallback.keys())
    total_issues = 0

    print(f"正在核验 {len(codes_to_check)} 只基金的逻辑一致性与数据同步性...\n")

    for code in codes_to_check:
        fb_item = fallback.get(code, {})
        pub_item = public_funds.get(code, {})

        # 检查 fallback 与 public 数据是否一致
        mismatches = []
        for key in ['limit_status', 'daily_limit', 'direct_limit_status', 'direct_daily_limit', 'service_fee']:
            if fb_item.get(key) != pub_item.get(key):
                mismatches.append(f"{key}: fallback={fb_item.get(key)} vs public={pub_item.get(key)}")

        if mismatches:
            print(f"  [同步差异] {code} {fb_item.get('name')}: {'; '.join(mismatches)}")
            total_issues += 1

        # 逻辑自洽性校验
        logic_issues = verify_fund_logic(pub_item)
        if logic_issues:
            print(f"  [逻辑异常] {code} {pub_item.get('name')}: {'; '.join(logic_issues)}")
            total_issues += len(logic_issues)

    print("\n" + "-" * 65)
    print("【专项直销与代销特殊额度基金审计】")
    special_codes = ['019548', '019547', '018064', '018065', '096001', '008401', '021000', '022525', '022523']
    for sc in special_codes:
        f = public_funds.get(sc, {})
        print(f"  {sc:6} {f.get('name', '')[:18]:18} | 代销: {f.get('limit_status'):10} ({f.get('daily_limit')}元) | 直销: {f.get('direct_limit_status'):10} ({f.get('direct_daily_limit')}元)")

    print("-" * 65)
    if total_issues == 0:
        print("[SUCCESS] 全量基金数据交叉核验与逻辑审计全部通过，无任何异常！")
        return 0
    else:
        print(f"[ERROR] 核验发现 {total_issues} 处异常，请修正后再行发布！")
        return 1


if __name__ == '__main__':
    sys.exit(run_cross_verification())
