import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scraper'))
from verify_quotas import (
    verify_fund_logic,
    verify_fund_profile,
    verify_fund_fees,
    verify_fund_metrics,
    verify_fund_complete,
    load_dataset,
    DATA_FALLBACK,
    DATA_PUBLIC
)


class TestVerifyQuotas(unittest.TestCase):
    def test_verify_fund_logic_valid(self):
        valid_fund = {
            'code': '019548',
            'name': '招商纳斯达克100ETF联接C',
            'limit_status': '限10元/日',
            'daily_limit': 10,
            'direct_limit_status': '限10元/日',
            'direct_daily_limit': 10,
        }
        issues = verify_fund_logic(valid_fund)
        self.assertEqual(len(issues), 0)

    def test_verify_fund_logic_suspended(self):
        suspended_fund = {
            'code': '018064',
            'name': '华夏标普500ETF联接A',
            'limit_status': '暂停申购',
            'daily_limit': 0,
            'direct_limit_status': '暂停申购',
            'direct_daily_limit': 0,
        }
        issues = verify_fund_logic(suspended_fund)
        self.assertEqual(len(issues), 0)

    def test_verify_fund_logic_mismatch(self):
        bad_fund = {
            'code': '999999',
            'name': '测试基金',
            'limit_status': '暂停申购',
            'daily_limit': 100,  # 错误：暂停申购但限额不为0
            'direct_limit_status': '限100元/日',
            'direct_daily_limit': 50,  # 错误：文字100与数值50不匹配
        }
        issues = verify_fund_logic(bad_fund)
        self.assertGreater(len(issues), 0)

    def test_verify_fund_profile(self):
        valid_profile = {
            'code': '096001',
            'name': '大成标普500等权指数(QDII)A类',
            'full_name': '大成标普500等权重指数证券投资基金',
            'share_class': 'A',
            'fund_type': '指数型-股票',
            'index_type': '标普500',
            'tracking_index': 'S&P 500 EQUAL WEIGHTED TOTAL RETURN',
            'scale': 7.3,
            'inception_date': '2011-03-23',
            'manager_company': '大成基金',
            'custodian': '中国银行',
            'fund_manager': '冉凌浩',
            'benchmark': '标普500等权重指数(全收益指数)',
        }
        issues = verify_fund_profile(valid_profile)
        self.assertEqual(len(issues), 0)

        # 缺失字段测试
        bad_profile = dict(valid_profile)
        del bad_profile['custodian']
        bad_profile['scale'] = -1
        issues = verify_fund_profile(bad_profile)
        self.assertGreater(len(issues), 0)

    def test_verify_fund_fees(self):
        # A类合法费率测试
        a_fund = {
            'code': '096001',
            'share_class': 'A',
            'mgmt_fee': 0.01,
            'custody_fee': 0.002,
            'sales_fee': 0.0,
            'purchase_fee': 0.015,
        }
        self.assertEqual(len(verify_fund_fees(a_fund)), 0)

        # C类合法费率测试
        c_fund = {
            'code': '008401',
            'share_class': 'C',
            'mgmt_fee': 0.01,
            'custody_fee': 0.002,
            'sales_fee': 0.003,
            'purchase_fee': 0.0,
        }
        self.assertEqual(len(verify_fund_fees(c_fund)), 0)

        # 南方021000 I类特惠费率测试
        i_fund = {
            'code': '021000',
            'share_class': 'I',
            'mgmt_fee': 0.005,
            'custody_fee': 0.0015,
            'sales_fee': 0.0001,  # 折后0.01%
            'purchase_fee': 0.0,
        }
        self.assertEqual(len(verify_fund_fees(i_fund)), 0)

        # 费率异常测试（A类收销售费，超额费率）
        bad_fee_fund = {
            'code': '096001',
            'share_class': 'A',
            'mgmt_fee': 0.05,  # 超标
            'custody_fee': 0.002,
            'sales_fee': 0.004, # A类不应有销售费
            'purchase_fee': 0.0,
        }
        self.assertGreater(len(verify_fund_fees(bad_fee_fund)), 0)

    def test_all_funds_sync_and_valid(self):
        fallback = load_dataset(DATA_FALLBACK)
        public_funds = load_dataset(DATA_PUBLIC)
        self.assertEqual(len(fallback), len(public_funds))
        for code, fb in fallback.items():
            pub = public_funds[code]
            # 基础信息比对
            for k in ['full_name', 'share_class', 'fund_type', 'index_type', 'manager_company', 'custodian']:
                self.assertEqual(fb.get(k), pub.get(k), f"{code} mismatch in {k}")
            # 费率比对
            for k in ['mgmt_fee', 'custody_fee', 'sales_fee', 'purchase_fee']:
                self.assertEqual(fb.get(k), pub.get(k), f"{code} mismatch in {k}")
            # 限额比对
            self.assertEqual(fb.get('limit_status'), pub.get('limit_status'))
            self.assertEqual(fb.get('daily_limit'), pub.get('daily_limit'))
            self.assertEqual(fb.get('direct_limit_status'), pub.get('direct_limit_status'))
            self.assertEqual(fb.get('direct_daily_limit'), pub.get('direct_daily_limit'))
            
            # 全维度完整性验证
            issues = verify_fund_complete(pub)
            self.assertEqual(len(issues), 0, f"Fund {code} has issues: {issues}")


if __name__ == '__main__':
    unittest.main()
