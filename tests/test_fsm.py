#!/usr/bin/env python3
"""
金融事件槽位有限状态机 (FinancialEventFSM) 单元测试
测试分句切分、渠道隔离、份额槽位绑定、目标值提取与动作状态转移
"""
import unittest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from scraper.fsm import FinancialEventFSM, FSMClause, FSMResult


class TestFinancialEventFSM(unittest.TestCase):
    """测试金融事件槽位有限状态机"""

    def test_wanjia_dual_quota(self):
        """测试万家基金双轨公告：代销10元，直销100元"""
        title = "关于万家纳斯达克100指数型发起式证券投资基金(QDII)调整大额申购限额的公告"
        content = (
            "为保护基金份额持有人利益，本基金自2026年9月29日起调整大额申购业务限额。"
            "投资者通过代销机构申购本基金A类及C类份额，单日单个基金账户累计申购金额不超过10元；"
            "投资者通过本公司直销柜台及网上直销平台申购本基金A类及C类份额，单日单个基金账户累计申购金额不超过100元。"
        )
        res_a = FinancialEventFSM.parse_announcement(content, title=title, fund_code='019441', share_class='A')
        self.assertEqual(res_a.direct_daily_limit, 100)
        self.assertEqual(res_a.direct_limit_status, '限100元/日')
        self.assertEqual(res_a.agency_daily_limit, 10)
        self.assertEqual(res_a.agency_limit_status, '限10元/日')

    def test_dacheng_dual_quota(self):
        """测试大成基金双轨公告：代销100元，直销1000元"""
        title = "大成标普500等权重指数证券投资基金调整大额申购限额的公告"
        content = (
            "大成基金管理有限公司决定自2026年3月18日起调整本基金的大额申购限额。"
            "在代销机构渠道，单日申购本基金A类及C类份额上限为100元；"
            "在本公司直销电子交易平台，单日申购上限为1000元人民币。"
        )
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='096001', share_class='A')
        self.assertEqual(res.direct_daily_limit, 1000)
        self.assertEqual(res.direct_limit_status, '限1000元/日')
        self.assertEqual(res.agency_daily_limit, 100)
        self.assertEqual(res.agency_limit_status, '限100元/日')

    def test_adjust_target_extraction(self):
        """测试由 X 调整为 Y 模式：必须准确提取调整后的目标 Y，不能被原限额 X 污染"""
        title = "招商基金关于调整大额申购限额的公告"
        content = (
            "自2026年8月1日起，招商纳斯达克100ETF联接基金直销电子交易平台的单日申购限额"
            "由100元下调至10元人民币。投资者应合理安排资金。"
        )
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='019548', share_class='C')
        self.assertEqual(res.direct_daily_limit, 10)
        self.assertEqual(res.direct_limit_status, '限10元/日')
        self.assertEqual(res.event_type, 'ADJUST')

    def test_code_table_exact_matching(self):
        """测试南方基金表格行精准匹配（如 021000）"""
        title = "南方标普500ETF联接基金相关业务公告"
        content = (
            "南方基金管理股份有限公司决定调整部分基金申购业务限制金额如下："
            "南方标普500联接A（004342）限制金额为10000元；"
            "南方标普500联接I（021000）在直销柜台限制金额200元；"
            "南方标普500联接C（004343）限制金额为5000元。"
        )
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='021000', share_class='I')
        self.assertEqual(res.direct_daily_limit, 200)
        self.assertEqual(res.direct_limit_status, '限200元/日')

    def test_direct_suspension_detection(self):
        """测试直销渠道暂停申购检测（带平台修饰符）"""
        title = "华夏基金关于暂停部分业务的公告"
        content = (
            "为保证基金平稳运作，华夏基金管理有限公司决定自2026年6月1日起，"
            "暂停在华夏直销电子交易平台的申购业务。代销渠道业务保持不变。"
        )
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='018064', share_class='A')
        self.assertEqual(res.direct_daily_limit, 0)
        self.assertEqual(res.direct_limit_status, '暂停申购')
        self.assertEqual(res.event_type, 'SUSPEND')

    def test_resumption_announcement(self):
        """测试恢复申购公告"""
        title = "博时基金关于恢复大额申购业务的公告"
        content = "博时标普500ETF联接基金自2026年5月10日起取消大额申购限制，恢复正常申购业务。"
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='006075', share_class='A')
        self.assertIsNone(res.direct_daily_limit)
        self.assertEqual(res.direct_limit_status, '开放申购')
        self.assertEqual(res.event_type, 'RESUME')

    def test_tianhong_d_class_not_offered_direct(self):
        """测试天弘D类基金直销渠道未上线/未开通判定"""
        title = "天弘纳斯达克100指数型发起式证券投资基金(QDII)之D类基金份额开放日常申购、赎回及定期定额投资业务公告"
        content = (
            "6. 本基金 D 类基金份额的销售机构。"
            "6.1 直销机构：本基金 D 类基金份额暂不上线直销机构。"
            "6.2 其他销售机构：详见基金管理人网站公示。"
        )
        res = FinancialEventFSM.parse_announcement(content, title=title, fund_code='022525', share_class='D')
        self.assertEqual(res.direct_daily_limit, 0)
        self.assertEqual(res.direct_limit_status, '未开通直销')
        self.assertEqual(res.event_type, 'NOT_OFFERED')

    def test_quota_sharing_combined(self):
        """测试多份额合并共享额度判定"""
        content = "本基金 A 类、C 类基金份额合并计算，单日每个基金账户累计申购金额合计不得超过 10 元人民币。"
        res = FinancialEventFSM.parse_announcement(content, title="", fund_code='019441', share_class='A')
        self.assertEqual(res.quota_sharing, 'SHARED')
        self.assertIn('合并计算', res.quota_shared_desc)

    def test_quota_sharing_separate(self):
        """测试多份额独立分别计算额度判定"""
        content = "对建信纳斯达克 100 指数型证券投资基金（QDII）人民币份额（代码：539001、012752、023422）单日累计高于 10 元的业务进行限制（不同份额分别计算）。"
        res = FinancialEventFSM.parse_announcement(content, title="", fund_code='023422', share_class='D')
        self.assertEqual(res.quota_sharing, 'INDEPENDENT')
        self.assertIn('独立计算', res.quota_shared_desc)

    def test_empty_content_safety(self):
        """测试空文本输入安全性"""
        res = FinancialEventFSM.parse_announcement("", title="", fund_code='000000')
        self.assertIsNone(res.direct_daily_limit)
        self.assertIsNone(res.direct_limit_status)
        self.assertEqual(len(res.clauses), 0)


if __name__ == '__main__':
    unittest.main()
