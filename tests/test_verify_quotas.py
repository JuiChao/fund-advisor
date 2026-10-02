import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scraper'))
from verify_quotas import verify_fund_logic, load_dataset, DATA_FALLBACK, DATA_PUBLIC


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

    def test_all_funds_sync_and_valid(self):
        fallback = load_dataset(DATA_FALLBACK)
        public_funds = load_dataset(DATA_PUBLIC)
        self.assertEqual(len(fallback), len(public_funds))
        for code, fb in fallback.items():
            pub = public_funds[code]
            self.assertEqual(fb.get('limit_status'), pub.get('limit_status'))
            self.assertEqual(fb.get('daily_limit'), pub.get('daily_limit'))
            self.assertEqual(fb.get('direct_limit_status'), pub.get('direct_limit_status'))
            self.assertEqual(fb.get('direct_daily_limit'), pub.get('direct_daily_limit'))
            issues = verify_fund_logic(pub)
            self.assertEqual(len(issues), 0, f"Fund {code} has logic issues: {issues}")


if __name__ == '__main__':
    unittest.main()
