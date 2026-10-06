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

    def test_verify_tianhong_d_class_channel_logic(self):
        """测试天弘D类份额渠道逻辑校验：直销必须为'未开通直销'，代销为'暂停申购'"""
        valid_tianhong_d = {
            'code': '022525',
            'name': '天弘纳斯达克100指数发起(QDII)D',
            'limit_status': '暂停申购',
            'daily_limit': 0,
            'direct_limit_status': '未开通直销',
            'direct_daily_limit': 0,
        }
        self.assertEqual(len(verify_fund_logic(valid_tianhong_d)), 0)

        # 错误情况：误标记为直销100元
        bad_tianhong_d = {
            'code': '022525',
            'name': '天弘纳斯达克100指数发起(QDII)D',
            'limit_status': '未开通代销',
            'daily_limit': 0,
            'direct_limit_status': '限100元/日',
            'direct_daily_limit': 100,
        }
        issues = verify_fund_logic(bad_tianhong_d)
        self.assertGreater(len(issues), 0)

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

    def test_verify_fund_logic_channel_invariant(self):
        # 直销额度低于代销额度时（如直销10元 vs 代销100元），违背渠道常理，应报错阻断
        abnormal_fund = {
            'code': '999999',
            'name': '异常渠道基金',
            'limit_status': '限100元/日',
            'daily_limit': 100,
            'direct_limit_status': '限10元/日',
            'direct_daily_limit': 10,
        }
        issues = verify_fund_logic(abnormal_fund)
        self.assertTrue(any('违背渠道常理' in iss for iss in issues))

        # 直销额度 >= 代销额度时，正常通过
        normal_fund = {
            'code': '999999',
            'name': '正常渠道基金',
            'limit_status': '限10元/日',
            'daily_limit': 10,
            'direct_limit_status': '限100元/日',
            'direct_daily_limit': 100,
        }
        self.assertEqual(len(verify_fund_logic(normal_fund)), 0)

    def test_dacheng_nasdaq_quotas(self):
        # 验证大成纳指 000834/008971 代销10元/日、直销100元/日及公告ID
        fallback = load_dataset(DATA_FALLBACK)
        for code in ['000834', '008971']:
            fund = fallback[code]
            self.assertEqual(fund['daily_limit'], 10, f"{code} agency daily limit should be 10")
            self.assertEqual(fund['limit_status'], '限10元/日', f"{code} agency status mismatch")
            self.assertEqual(fund['direct_daily_limit'], 100, f"{code} direct daily limit should be 100")
            self.assertEqual(fund['direct_limit_status'], '限100元/日', f"{code} direct status mismatch")
            self.assertEqual(fund['limit_announcement_id'], 'AN202606031823188725')

    def test_extract_independent_clause_quotas(self):
        # 验证独立子句语义隔离：直销与代销同篇公告中绝不串行穿透
        from verify_quotas import extract_independent_clause_quotas
        notice_text = (
            "自2026年06月04日起，投资者通过本公司直销机构（APP、微信公众号和直销柜台等）"
            "申购本基金A/C类份额单日每个账户累计申购金额应不超过100元人民币。"
            "自2026年06月04日起，投资者通过代销渠道申购本基金A/C类份额单日每个账户"
            "累计申购金额应不超过10元人民币。"
        )
        res = extract_independent_clause_quotas(notice_text)
        self.assertEqual(res['direct'], [100])
        self.assertEqual(res['agency'], [10])

    def test_adjustment_and_resumption_patterns(self):
        import re
        # 1. 测试“由X元调整为Y元”提取Y
        text_adjust = "自2026年10月08日起，通过本公司直销机构申购本基金单日累计金额由原来的10元调整为1000元人民币"
        m_adjust = re.search(
            r'(?:直销(?:机构|渠道|平台|柜台)?.*?)?由\D{0,15}?([0-9,]+(?:\.\d+)?)\s*元.*?(?:调整为|上调至|下调至|调整至)\s*(?:人民币)?\s*([0-9,]+(?:\.\d+)?)\s*元',
            text_adjust
        )
        self.assertIsNotNone(m_adjust)
        self.assertEqual(int(m_adjust.group(2)), 1000)

        # 2. 测试恢复申购公告识别（支持基金全称穿插在中间）
        title_resume = "关于恢复办理万家纳斯达克100指数型发起式证券投资基金(QDII)大额申购业务的公告"
        is_resumption = ('恢复' in title_resume and '申购' in title_resume) or \
                        ('取消' in title_resume and any(k in title_resume for k in ['限额', '上限', '规模', '额度']))
        self.assertTrue(is_resumption)

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

