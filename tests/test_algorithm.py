#!/usr/bin/env python3
"""
核心算法单元测试
测试 score_fund、rank_funds、allocate_ideal、allocate_practical

运行: cd fund-advisor && python -m pytest tests/test_algorithm.py -v
  或: cd fund-advisor && python -m unittest tests.test_algorithm -v
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 将项目根目录加入 sys.path 以便导入 scraper.simulate
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 切换工作目录到项目根（simulate.py 使用相对路径读取 config）
os.chdir(PROJECT_ROOT)

from scraper.simulate import (
    score_fund, rank_funds, allocate_ideal, allocate_practical,
    pick_funds_by_style, CONFIG, TRADING_DAYS, BASE_BUDGET
)


class TestScoreFund(unittest.TestCase):
    """测试基金评分函数"""

    def test_perfect_fund_gets_high_score(self):
        """费率最低、跟踪误差最小、规模适中的基金应得高分"""
        fund = {
            'mgmt_fee': 0.004, 'custody_fee': 0.0001,  # 极低费率
            'tracking_error': 0.005,                     # 极低跟踪误差
            'scale': 50,                                 # 最优规模区间
            'return_3yr': 0.8,                           # 高收益
            'morningstar': 5,                            # 满星
            'purchase_fee': 0.0001,                      # 极低申购费
        }
        score = score_fund(fund)
        self.assertGreater(score, 90, f"优质基金评分应 >90，实际 {score}")

    def test_poor_fund_gets_low_score(self):
        """高费率、高跟踪误差、小规模的基金应得低分"""
        fund = {
            'mgmt_fee': 0.025, 'custody_fee': 0.008,
            'tracking_error': 0.12,
            'scale': 0.5,
            'return_3yr': 0.1,
            'morningstar': 0,
            'purchase_fee': 0.015,
        }
        score = score_fund(fund)
        self.assertLess(score, 50, f"劣质基金评分应 <50，实际 {score}")

    def test_score_range_reasonable(self):
        """评分结果应在合理范围内（morningstar 5星时单项可达125，总分可能略超100）"""
        # 极端低值
        worst = {
            'mgmt_fee': 0.1, 'custody_fee': 0.05,
            'tracking_error': 0.5, 'scale': 0.01,
            'return_3yr': -0.5, 'morningstar': 0,
            'purchase_fee': 0.1,
        }
        score_worst = score_fund(worst)
        self.assertGreaterEqual(score_worst, 0, f"最低分应 >=0，实际 {score_worst}")

        # 极端高值（morningstar=5 时单项分数为125，总分可能略超100）
        best = {
            'mgmt_fee': 0.001, 'custody_fee': 0.0001,
            'tracking_error': 0.001, 'scale': 50,
            'return_3yr': 5.0, 'morningstar': 5,
            'purchase_fee': 0,
        }
        score_best = score_fund(best)
        self.assertGreater(score_best, 90, f"最高分应 >90，实际 {score_best}")
        self.assertLessEqual(score_best, 110, f"最高分应 <=110，实际 {score_best}")

    def test_null_fields_use_defaults(self):
        """缺失字段应使用默认值且不报错"""
        fund = {'code': '000001', 'name': '测试基金'}
        score = score_fund(fund)
        self.assertIsInstance(score, float, "缺失字段时仍应返回数值")

    def test_fee_dominates_score(self):
        """费率权重最大(0.35)，低费率基金应比高费率基金评分高（其他条件相同）"""
        base = {
            'tracking_error': 0.01, 'scale': 50,
            'return_3yr': 0.5, 'morningstar': 3,
            'purchase_fee': 0.001,
        }
        low_fee = {**base, 'mgmt_fee': 0.003, 'custody_fee': 0.0005}
        high_fee = {**base, 'mgmt_fee': 0.02, 'custody_fee': 0.005}
        self.assertGreater(score_fund(low_fee), score_fund(high_fee),
                          "低费率基金评分应高于高费率基金")

    def test_scale_scoring_boundaries(self):
        """规模评分的边界检查"""
        sc = CONFIG['scoring']['scale']
        # 最优区间
        score_optimal = score_fund({
            'mgmt_fee': 0.008, 'custody_fee': 0.002, 'tracking_error': 0.01,
            'scale': (sc['optimal_min'] + sc['optimal_max']) / 2,
            'return_3yr': 0.5, 'morningstar': 3, 'purchase_fee': 0.001,
        })
        # 小规模
        score_small = score_fund({
            'mgmt_fee': 0.008, 'custody_fee': 0.002, 'tracking_error': 0.01,
            'scale': sc['small_threshold'] - 0.1,
            'return_3yr': 0.5, 'morningstar': 3, 'purchase_fee': 0.001,
        })
        self.assertGreater(score_optimal, score_small,
                          "最优规模基金评分应高于小规模基金")


class TestRankFunds(unittest.TestCase):
    """测试基金排名函数"""

    def test_ranking_order(self):
        """排名应按评分降序"""
        funds = [
            {'code': 'A', 'mgmt_fee': 0.02, 'custody_fee': 0.005, 'tracking_error': 0.05},
            {'code': 'B', 'mgmt_fee': 0.003, 'custody_fee': 0.0005, 'tracking_error': 0.005, 'scale': 50},
            {'code': 'C', 'mgmt_fee': 0.008, 'custody_fee': 0.002, 'tracking_error': 0.01, 'scale': 30},
        ]
        ranked = rank_funds(funds)
        codes = [f['code'] for f in ranked]
        self.assertEqual(codes, ['B', 'C', 'A'], f"排名应为 B>C>A，实际 {codes}")

    def test_rank_assigned(self):
        """每只基金应被分配 rank 字段"""
        funds = [
            {'code': 'A', 'mgmt_fee': 0.003, 'custody_fee': 0.0005, 'tracking_error': 0.005, 'scale': 50},
            {'code': 'B', 'mgmt_fee': 0.02, 'custody_fee': 0.005, 'tracking_error': 0.05},
        ]
        ranked = rank_funds(funds)
        self.assertEqual(ranked[0]['rank'], 1)
        self.assertEqual(ranked[1]['rank'], 2)

    def test_empty_list(self):
        """空列表不应报错"""
        ranked = rank_funds([])
        self.assertEqual(ranked, [])


class TestAllocateIdeal(unittest.TestCase):
    """测试理论分配函数"""

    def test_budget_distributed(self):
        """预算应按权重分配"""
        items = [
            {'fund': {'code': 'A', 'name': '基金A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.6},
            {'fund': {'code': 'B', 'name': '基金B', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 70, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.4},
        ]
        allocs = allocate_ideal(items, BASE_BUDGET)
        total_monthly = sum(a['monthly'] for a in allocs)
        self.assertAlmostEqual(total_monthly, BASE_BUDGET, delta=1,
                              msg=f"月度分配总额应≈预算 {BASE_BUDGET}")

    def test_weights_sum_to_one(self):
        """actual_weight 之和应≈1"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.6},
            {'fund': {'code': 'B', 'name': 'B', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 70, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.4},
        ]
        allocs = allocate_ideal(items, 2000)
        total_weight = sum(a.get('actual_weight', 0) for a in allocs)
        self.assertAlmostEqual(total_weight, 1.0, places=2,
                              msg=f"实际权重和应≈1.0，实际 {total_weight}")

    def test_no_exceeds_limit(self):
        """理论分配不应触发 exceeds_limit"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '正常',
                       'daily_limit': 10}, 'weight': 1.0},
        ]
        allocs = allocate_ideal(items, 10000)
        self.assertFalse(allocs[0]['exceeds_limit'], "理论分配不应触发限购标记")


class TestAllocatePractical(unittest.TestCase):
    """测试实际分配函数"""

    def test_suspended_fund_excluded(self):
        """暂停申购的基金应分配为0"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '暂停申购',
                       'daily_limit': 0}, 'weight': 0.5},
            {'fund': {'code': 'B', 'name': 'B', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 70, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.5},
        ]
        allocs = allocate_practical(items, 2000)
        a_alloc = next(a for a in allocs if a['code'] == 'A')
        b_alloc = next(a for a in allocs if a['code'] == 'B')
        self.assertEqual(a_alloc['monthly'], 0, "暂停基金月分配应为0")
        self.assertGreater(b_alloc['monthly'], 0, "正常基金月分配应>0")

    def test_limit_respected(self):
        """受限基金的每日分配不应超过 daily_limit"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '限100元/日',
                       'daily_limit': 100}, 'weight': 1.0},
        ]
        allocs = allocate_practical(items, 100000)
        a = allocs[0]
        self.assertLessEqual(a['daily'], 100, f"每日分配不应超过限额 100，实际 {a['daily']}")
        self.assertTrue(a['exceeds_limit'], "大预算受限基金应标记 exceeds_limit")

    def test_budget_redistribution(self):
        """受限基金的超额资金应重新分配给其他基金"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 90, 'limit_status': '限100元/日',
                       'daily_limit': 100}, 'weight': 0.5},
            {'fund': {'code': 'B', 'name': 'B', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.5},
        ]
        budget = 10000
        allocs = allocate_practical(items, budget)
        a_alloc = next(a for a in allocs if a['code'] == 'A')
        b_alloc = next(a for a in allocs if a['code'] == 'B')
        # A 被限制在 100元/日 × 22日 = 2200元/月
        self.assertLessEqual(a_alloc['monthly'], 100 * TRADING_DAYS + 1,
                            "A 的月分配应受限于 daily_limit × trading_days")
        # B 应吸收 A 无法使用的超额资金
        self.assertGreater(b_alloc['monthly'], budget * 0.5,
                          "B 应吸收 A 的超额资金，月分配应 > 预算的一半")

    def test_all_suspended(self):
        """所有基金都暂停时不应崩溃"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '暂停申购',
                       'daily_limit': 0}, 'weight': 1.0},
        ]
        allocs = allocate_practical(items, 2000)
        self.assertEqual(len(allocs), 1, "应返回1条记录")
        self.assertEqual(allocs[0]['monthly'], 0, "全部暂停时月分配为0")

    def test_total_not_exceed_budget(self):
        """实际分配总额不应超过预算"""
        items = [
            {'fund': {'code': 'A', 'name': 'A', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 90, 'limit_status': '限50元/日',
                       'daily_limit': 50}, 'weight': 0.5},
            {'fund': {'code': 'B', 'name': 'B', 'mgmt_fee': 0.005, 'custody_fee': 0.001,
                       'tracking_error': 0.01, 'score': 80, 'limit_status': '正常',
                       'daily_limit': None}, 'weight': 0.5},
        ]
        budget = 5000
        allocs = allocate_practical(items, budget)
        total = sum(a['monthly'] for a in allocs)
        self.assertLessEqual(total, budget + 1,
                            f"实际分配总额应 <= 预算 {budget}，实际 {total}")


class TestConfigConsistency(unittest.TestCase):
    """测试配置一致性"""

    def test_weights_sum_to_one(self):
        """评分权重之和应=1.0"""
        weights = CONFIG['scoring']['weights']
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=4,
                              msg=f"评分权重和应=1.0，实际 {total}")

    def test_strategies_exist(self):
        """应至少有3种策略定义"""
        self.assertGreaterEqual(len(CONFIG['strategies']), 3,
                               "应至少定义3种投资策略")

    def test_years_range_valid(self):
        """年限范围应递增且合理"""
        years = CONFIG['simulation']['years_range']
        self.assertEqual(years, sorted(years), "年限范围应递增")
        self.assertGreaterEqual(years[0], 1, "最小年限应 >=1")
        self.assertLessEqual(years[-1], 50, "最大年限应 <=50")

    def test_correlation_valid(self):
        """相关系数应在 [0, 1) 范围"""
        rho = CONFIG['simulation']['correlation_nq_sp']
        self.assertGreaterEqual(rho, 0, "相关系数应 >=0")
        self.assertLess(rho, 1, "相关系数应 <1")

    def test_sim_counts_positive(self):
        """模拟次数应为正整数"""
        self.assertIsInstance(CONFIG['simulation']['n_sims_python'], int)
        self.assertGreater(CONFIG['simulation']['n_sims_python'], 0)
        self.assertIsInstance(CONFIG['simulation']['n_sims_frontend'], int)
        self.assertGreater(CONFIG['simulation']['n_sims_frontend'], 0)


if __name__ == '__main__':
    unittest.main()
