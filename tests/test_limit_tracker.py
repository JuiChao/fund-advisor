#!/usr/bin/env python3
"""
QDII 限购变更追踪器单元测试
"""
import unittest
import os
import sys
import tempfile
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scraper'))
from limit_tracker import (
    parse_limit_val,
    classify_channel_direction,
    diff_fund_limits,
    find_substitutes,
    update_limit_changes_file
)


class TestLimitTracker(unittest.TestCase):
    def setUp(self):
        self.mock_funds = [
            {
                'code': '019441',
                'name': '万家纳斯达克100指数发起式(QDII)A',
                'index_type': '纳斯达克100',
                'share_class': 'A',
                'limit_status': '限10元/日',
                'daily_limit': 10,
                'direct_limit_status': '限100元/日',
                'direct_daily_limit': 100,
                'mgmt_fee': 0.005,
                'custody_fee': 0.0015,
                'sales_fee': 0.0,
                'score': 85.0
            },
            {
                'code': '000834',
                'name': '大成纳斯达克100ETF联接(QDII)A',
                'index_type': '纳斯达克100',
                'share_class': 'A',
                'limit_status': '限100元/日',
                'daily_limit': 100,
                'direct_limit_status': '限1000元/日',
                'direct_daily_limit': 1000,
                'mgmt_fee': 0.005,
                'custody_fee': 0.0015,
                'sales_fee': 0.0,
                'score': 90.0
            },
            {
                'code': '096001',
                'name': '大成标普500等权指数(QDII)A类',
                'index_type': '标普500',
                'share_class': 'A',
                'limit_status': '限1000元/日',
                'daily_limit': 1000,
                'direct_limit_status': '限1000元/日',
                'direct_daily_limit': 1000,
                'mgmt_fee': 0.008,
                'custody_fee': 0.002,
                'sales_fee': 0.0,
                'score': 88.0
            }
        ]

    def test_parse_limit_val(self):
        self.assertEqual(parse_limit_val(100, '限100元/日'), 100.0)
        self.assertEqual(parse_limit_val(None, '暂停申购'), 0.0)
        self.assertEqual(parse_limit_val(None, '限500元/日'), 500.0)
        self.assertEqual(parse_limit_val(None, '开放申购'), 999999999.0)

    def test_classify_direction_relaxed(self):
        # 暂停 -> 恢复限额
        d = classify_channel_direction('暂停申购', None, '限100元/日', 100)
        self.assertEqual(d, 'RELAXED')

        # 额度上调 10 -> 100
        d = classify_channel_direction('限10元/日', 10, '限100元/日', 100)
        self.assertEqual(d, 'RELAXED')

    def test_classify_direction_tightened(self):
        # 额度下调 100 -> 10
        d = classify_channel_direction('限100元/日', 100, '限10元/日', 10)
        self.assertEqual(d, 'TIGHTENED')

        # 开放 -> 暂停
        d = classify_channel_direction('开放申购', None, '暂停申购', None)
        self.assertEqual(d, 'TIGHTENED')

    def test_diff_fund_limits_detects_changes(self):
        old_map = {
            '019441': {
                'code': '019441',
                'name': '万家纳斯达克100指数发起式(QDII)A',
                'index_type': '纳斯达克100',
                'limit_status': '限100元/日',
                'daily_limit': 100,
                'direct_limit_status': '限1000元/日',
                'direct_daily_limit': 1000
            }
        }
        # 新数据中 019441 额度下调为 10 和 100
        new_list = [self.mock_funds[0], self.mock_funds[1]]
        changes = diff_fund_limits(old_map, new_list, today_str='2026-10-07')

        self.assertEqual(len(changes), 1)
        ch = changes[0]
        self.assertEqual(ch['code'], '019441')
        self.assertEqual(ch['change_type'], 'TIGHTENED')
        self.assertEqual(ch['agency']['before_limit'], 100)
        self.assertEqual(ch['agency']['after_limit'], 10)
        self.assertIn('000834', [s['code'] for s in ch['substitutes']])

    def test_find_substitutes_filters_same_index(self):
        subs = find_substitutes(self.mock_funds[0], self.mock_funds)
        self.assertTrue(len(subs) >= 1)
        # 应该推荐 000834，而不是标普500的 096001
        self.assertEqual(subs[0]['code'], '000834')
        self.assertEqual(subs[0]['index_type'], '纳斯达克100')

    def test_update_limit_changes_file_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_f_path = os.path.join(tmpdir, 'funds_old.json')
            ch_f_path = os.path.join(tmpdir, 'limit_changes.json')

            old_data = [
                {
                    'code': '019441',
                    'limit_status': '限100元/日',
                    'daily_limit': 100,
                    'direct_limit_status': '限1000元/日',
                    'direct_daily_limit': 1000
                }
            ]
            with open(old_f_path, 'w', encoding='utf-8') as f:
                json.dump(old_data, f)

            result, changes = update_limit_changes_file(
                self.mock_funds,
                old_funds_path=old_f_path,
                changes_path=ch_f_path
            )

            self.assertEqual(result['today_count'], 1)
            self.assertEqual(len(changes), 1)
            self.assertTrue(os.path.exists(ch_f_path))

            # 二次运行去重测试
            result2, changes2 = update_limit_changes_file(
                self.mock_funds,
                old_funds_path=old_f_path,
                changes_path=ch_f_path
            )
            # 今天仍是1条，不重复叠加
            self.assertEqual(result2['today_count'], 1)


if __name__ == '__main__':
    unittest.main()
