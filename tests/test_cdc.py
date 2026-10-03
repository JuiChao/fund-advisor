#!/usr/bin/env python3
"""
CDC 增量变更流与并发抓取单元测试
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scraper'))
from scrape import (
    detect_cdc_affected_funds,
    scrape_single_fund_record,
    load_cached_funds,
    FUND_LIST
)


class TestCDCIncremental(unittest.TestCase):
    def setUp(self):
        self.universe_codes = ['019441', '096001', '000834', '018064']
        self.fallback_data = {
            '019441': {'name': '万家纳斯达克100指数发起(QDII)A', 'index_type': '纳斯达克100'},
            '096001': {'name': '大成标普500等权指数(QDII)A类', 'index_type': '标普500'},
            '000834': {'name': '大成纳斯达克100ETF联接(QDII)A', 'index_type': '纳斯达克100'},
            '018064': {'name': '华夏标普500ETF发起式联接(QDII)A', 'index_type': '标普500'},
        }

    def test_detect_affected_funds_by_fundcode(self):
        feed_items = [
            {
                'FUNDCODE': '019441',
                'TITLE': '关于万家纳斯达克100指数发起(QDII)A调整大额申购业务限额的公告',
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030001'
            },
            {
                'FUNDCODE': '999999',  # 非宇宙标的
                'TITLE': '关于某某股票型基金暂停大额申购的公告',
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030002'
            }
        ]
        affected = detect_cdc_affected_funds(feed_items, self.universe_codes, self.fallback_data)
        self.assertIn('019441', affected)
        self.assertNotIn('999999', affected)

    def test_detect_affected_funds_by_title_mention(self):
        feed_items = [
            {
                'FUNDCODE': None,  # FUNDCODE 为空但标题提及代码
                'TITLE': '关于大成标普500(096001)恢复大额申购业务的公告',
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030003'
            }
        ]
        affected = detect_cdc_affected_funds(feed_items, self.universe_codes, self.fallback_data)
        self.assertIn('096001', affected)

    def test_ignore_holiday_announcements(self):
        feed_items = [
            {
                'FUNDCODE': '018064',
                'TITLE': '关于主要投资市场节假日暂停申购、赎回等业务的公告',
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030004'
            },
            {
                'FUNDCODE': '000834',
                'TITLE': '关于境外非交易日暂停申购的公告',
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030005'
            }
        ]
        affected = detect_cdc_affected_funds(feed_items, self.universe_codes, self.fallback_data)
        self.assertEqual(len(affected), 0)

    def test_ignore_unrelated_announcements(self):
        feed_items = [
            {
                'FUNDCODE': '019441',
                'TITLE': '2026年第2季度报告',  # 非限额/申购类公告
                'PUBLISHDATEDesc': '2026-10-03',
                'ID': 'AN202610030006'
            }
        ]
        affected = detect_cdc_affected_funds(feed_items, self.universe_codes, self.fallback_data)
        self.assertEqual(len(affected), 0)

    @patch('scrape.scrape_fund_page')
    def test_scrape_single_fund_record_incremental_reuses_cache(self, mock_fund_page):
        mock_fund_page.return_value = {
            'return_1yr': 0.185,
            'volatility': 0.22,
            'tracking_error': 0.005,
            'scale': 25.5
        }
        fallback_item = {
            'code': '019441',
            'name': '万家纳斯达克100指数发起(QDII)A',
            'full_name': '万家纳斯达克100指数证券投资基金',
            'mgmt_fee': 0.005,
            'custody_fee': 0.0015,
            'sales_fee': 0.0,
            'purchase_fee': 0.0012,
            'daily_limit': 10,
            'limit_status': '限10元/日',
            'direct_daily_limit': 100,
            'direct_limit_status': '限100元/日',
        }
        cached_item = dict(fallback_item)

        merged, total_fields = scrape_single_fund_record(
            code='019441',
            index_type='纳斯达克100',
            fallback_item=fallback_item,
            cached_item=cached_item,
            full_refresh=False
        )

        # 验证行情指标已更新
        self.assertEqual(merged['return_1yr'], 0.185)
        self.assertEqual(merged['volatility'], 0.22)
        # 验证静态档案与直销限额从缓存精准复用
        self.assertEqual(merged['mgmt_fee'], 0.005)
        self.assertEqual(merged['custody_fee'], 0.0015)
        self.assertEqual(merged['daily_limit'], 10)
        self.assertEqual(merged['limit_status'], '限10元/日')
        self.assertEqual(merged['direct_daily_limit'], 100)
        self.assertEqual(merged['direct_limit_status'], '限100元/日')


if __name__ == '__main__':
    unittest.main()
