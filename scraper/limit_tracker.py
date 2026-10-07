#!/usr/bin/env python3
"""
QDII 基金申购限购变更追踪与公告生成模块 (Quota Intelligence Tracker)
功能：
1. 比对每日抓取前后 funds.json 中代销/直销限购状态及额度数值变动
2. 智能分类变动性质 (放宽/收紧/恢复/暂停/渠道分化)
3. 自动匹配同指数低费率优质平替基金 (Substitutes)
4. 持久化 public/data/limit_changes.json 供前端全景展示与看板渲染
"""

import os
import json
import re
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))
LIMIT_CHANGES_FILE = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'limit_changes.json')
FUNDS_FILE = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'funds.json')


def parse_limit_val(limit_val, limit_status):
    """提取额度数值，辅助判定升降"""
    if isinstance(limit_val, (int, float)):
        return float(limit_val)
    if not limit_status:
        return None
    status_str = str(limit_status).strip()
    if '暂停' in status_str or '未开通' in status_str:
        return 0.0
    if '开放' in status_str and '大额' not in status_str and '限' not in status_str:
        return 999999999.0  # 视为无限制
    # 尝试正则提取如 "限100元/日"
    m = re.search(r'(\d+(?:\.\d+)?)', status_str)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def classify_channel_direction(old_status, old_limit, new_status, new_limit):
    """
    判断单渠道变动方向：
    返回: 'RELAXED' (放宽/恢复), 'TIGHTENED' (收紧/暂停), or None (无实质变动)
    """
    old_status = (old_status or '').strip()
    new_status = (new_status or '').strip()

    if old_status == new_status and old_limit == new_limit:
        return None

    old_num = parse_limit_val(old_limit, old_status)
    new_num = parse_limit_val(new_limit, new_status)

    old_is_paused = ('暂停' in old_status) or (old_num == 0.0)
    new_is_paused = ('暂停' in new_status) or (new_num == 0.0)

    # 1. 暂停状态变化
    if old_is_paused and not new_is_paused:
        return 'RELAXED'
    if not old_is_paused and new_is_paused:
        return 'TIGHTENED'

    # 2. 数值对比
    if old_num is not None and new_num is not None:
        if new_num > old_num:
            return 'RELAXED'
        elif new_num < old_num:
            return 'TIGHTENED'

    # 3. 语义判断
    if '恢复' in new_status or '开放' in new_status:
        return 'RELAXED'
    if '暂停' in new_status:
        return 'TIGHTENED'

    # 默认如果有文案变更
    return 'CHANGED'


def find_substitutes(target_fund, all_funds, max_count=3):
    """
    为限购/额度收紧基金寻找同指数优质平替标的：
    1. 同一标的指数 (如 纳斯达克100 或 标普500)
    2. 排除自身
    3. 代销或直销未完全暂停
    4. 综合费率最低且额度较高
    """
    target_idx = target_fund.get('index_type')
    target_code = target_fund.get('code')
    if not target_idx or not all_funds:
        return []

    candidates = []
    for f in all_funds:
        if f.get('code') == target_code:
            continue
        if f.get('index_type') != target_idx:
            continue

        agency_st = f.get('limit_status') or ''
        direct_st = f.get('direct_limit_status') or ''
        agency_paused = ('暂停' in agency_st) or ('未开通' in agency_st)
        direct_paused = ('暂停' in direct_st) or ('未开通' in direct_st) or (not direct_st)

        # 双渠道均暂停的不能做平替
        if agency_paused and direct_paused:
            continue

        # 计算总费率
        mgmt = f.get('mgmt_fee', 0) or 0
        cust = f.get('custody_fee', 0) or 0
        sales = f.get('sales_fee', 0) or 0
        total_fee = round(mgmt + cust + sales, 4)

        # 评分或额度
        agency_limit = f.get('daily_limit') or 0
        direct_limit = f.get('direct_daily_limit') or 0
        max_quota = max(agency_limit, direct_limit)

        candidates.append({
            'code': f.get('code'),
            'name': f.get('name'),
            'share_class': f.get('share_class', ''),
            'index_type': f.get('index_type'),
            'total_fee': total_fee,
            'limit_status': agency_st,
            'direct_limit_status': direct_st,
            'daily_limit': f.get('daily_limit'),
            'direct_daily_limit': f.get('direct_daily_limit'),
            'max_quota': max_quota,
            'score': f.get('score', 0)
        })

    # 排序规则：额度充足度降序，费率升序，评分降序
    candidates.sort(key=lambda x: (-x['max_quota'], x['total_fee'], -x['score']))
    return candidates[:max_count]


def diff_fund_limits(old_funds_map, new_funds_list, today_str=None):
    """
    比对新旧基金列表中的限购状态变动，返回变动记录列表
    """
    if today_str is None:
        today_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')

    changes = []
    for new_f in new_funds_list:
        code = new_f.get('code')
        old_f = old_funds_map.get(code)
        if not old_f:
            continue  # 新纳入标的，不作为限购"变更"记入历史

        old_agency_st = old_f.get('limit_status')
        new_agency_st = new_f.get('limit_status')
        old_agency_limit = old_f.get('daily_limit')
        new_agency_limit = new_f.get('daily_limit')

        old_direct_st = old_f.get('direct_limit_status')
        new_direct_st = new_f.get('direct_limit_status')
        old_direct_limit = old_f.get('direct_daily_limit')
        new_direct_limit = new_f.get('direct_daily_limit')

        agency_dir = classify_channel_direction(
            old_agency_st, old_agency_limit,
            new_agency_st, new_agency_limit
        )
        direct_dir = classify_channel_direction(
            old_direct_st, old_direct_limit,
            new_direct_st, new_direct_limit
        )

        # 若两个渠道都无变动，则跳过
        if agency_dir is None and direct_dir is None:
            continue

        # 综合判定整体变动类型
        if agency_dir == 'RELAXED' or direct_dir == 'RELAXED':
            if agency_dir == 'TIGHTENED' or direct_dir == 'TIGHTENED':
                change_type = 'CHANNEL_DIV'
                type_label = '渠道分化调整'
            else:
                change_type = 'RELAXED'
                type_label = '额度放宽 / 恢复申购'
        elif agency_dir == 'TIGHTENED' or direct_dir == 'TIGHTENED':
            change_type = 'TIGHTENED'
            type_label = '额度下调 / 暂停申购'
        else:
            change_type = 'MODIFIED'
            type_label = '限购状态变更'

        # 生成语义化简报
        parts = []
        if agency_dir:
            parts.append(f"代销: {old_agency_st or '未记录'} ➔ {new_agency_st or '未记录'}")
        if direct_dir:
            parts.append(f"直销: {old_direct_st or '未记录'} ➔ {new_direct_st or '未记录'}")
        summary_text = '；'.join(parts)

        # 查找智能平替
        subs = find_substitutes(new_f, new_funds_list, max_count=3)

        ann_id = new_f.get('limit_announcement_id') or old_f.get('limit_announcement_id')
        ann_url = new_f.get('announcement_url') or (f"https://data.eastmoney.com/notices/detail/{code}/{ann_id}.html" if ann_id else f"https://fundf10.eastmoney.com/jjgg_{code}.html")
        record_date = new_f.get('effective_date') or new_f.get('announcement_pub_date') or today_str

        changes.append({
            'date': record_date,
            'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%dT%H:%M:%S'),
            'code': code,
            'name': new_f.get('name'),
            'index_type': new_f.get('index_type'),
            'share_class': new_f.get('share_class', ''),
            'change_type': change_type,
            'change_type_label': type_label,
            'agency': {
                'before_status': old_agency_st or '—',
                'after_status': new_agency_st or '—',
                'before_limit': old_agency_limit,
                'after_limit': new_agency_limit,
                'direction': agency_dir,
            },
            'direct': {
                'before_status': old_direct_st or '—',
                'after_status': new_direct_st or '—',
                'before_limit': old_direct_limit,
                'after_limit': new_direct_limit,
                'direction': direct_dir,
            },
            'summary': summary_text,
            'announcement_id': ann_id,
            'announcement_url': ann_url,
            'substitutes': subs
        })

    return changes


def load_limit_changes(filepath=LIMIT_CHANGES_FILE):
    """读取历史限购变更数据"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {
        'last_updated': datetime.now(BEIJING_TZ).strftime('%Y-%m-%dT%H:%M:%S'),
        'today_count': 0,
        'recent_7d_count': 0,
        'history': []
    }


def update_limit_changes_file(new_funds, old_funds_path=FUNDS_FILE, changes_path=LIMIT_CHANGES_FILE):
    """
    增量检测并更新 limit_changes.json
    """
    old_funds_map = {}
    if os.path.exists(old_funds_path):
        try:
            with open(old_funds_path, 'r', encoding='utf-8') as f:
                raw_old = json.load(f)
                if isinstance(raw_old, list):
                    for f_item in raw_old:
                        if isinstance(f_item, dict) and 'code' in f_item:
                            old_funds_map[f_item['code']] = f_item
        except Exception as e:
            print(f"  [WARN] 读取旧基金数据失败: {e}")

    today_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    new_changes = diff_fund_limits(old_funds_map, new_funds, today_str=today_str)

    data = load_limit_changes(changes_path)
    existing_history = data.get('history', [])

    # 如果今天该基金已有记录，用最新检测结果更新或去重
    updated_history = []
    new_codes_today = {c['code'] for c in new_changes}

    for item in existing_history:
        # 保留不是今天的，或者今天但不在 new_codes_today 中的
        if item.get('date') == today_str and item.get('code') in new_codes_today:
            continue
        updated_history.append(item)

    # 追加今日新变动到最顶部 (时间倒序)
    updated_history = new_changes + updated_history

    # 保留最近 90 天记录，防止文件无限膨胀
    updated_history = updated_history[:100]

    # 计算统计指标
    today_count = sum(1 for item in updated_history if item.get('date') == today_str)

    # 计算最近 7 天变动数
    d7_str = (datetime.now(BEIJING_TZ) - timedelta(days=7)).strftime('%Y-%m-%d')
    recent_7d_count = sum(1 for item in updated_history if (item.get('date') or '') >= d7_str)

    result_data = {
        'last_updated': datetime.now(BEIJING_TZ).strftime('%Y-%m-%dT%H:%M:%S'),
        'today_date': today_str,
        'today_count': today_count,
        'recent_7d_count': recent_7d_count,
        'total_monitored': len(new_funds),
        'history': updated_history
    }

    os.makedirs(os.path.dirname(changes_path), exist_ok=True)
    with open(changes_path, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return result_data, new_changes
