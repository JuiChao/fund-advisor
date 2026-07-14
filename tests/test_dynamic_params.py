#!/usr/bin/env python3
"""
动态参数计算单元测试
测试 calc_dynamic_params 函数

运行: cd fund-advisor && python -m unittest tests.test_dynamic_params -v
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from scraper.simulate import calc_dynamic_params, PARAMS_FALLBACK


class TestCalcDynamicParams(unittest.TestCase):
    """测试动态参数计算函数"""

    def test_dynamic_mode_with_enough_funds(self):
        """有足够基金数据时应使用动态参数"""
        funds = []
        # 5只纳指基金，近3年收益 30%-50%，波动率 20%-30%
        for i in range(5):
            funds.append({
                'index_type': '纳斯达克100',
                'return_3yr': 0.3 + i * 0.05,
                'volatility': 0.20 + i * 0.02,
            })
        # 4只标普基金
        for i in range(4):
            funds.append({
                'index_type': '标普500',
                'return_3yr': 0.2 + i * 0.05,
                'volatility': 0.15 + i * 0.02,
            })

        params, source = calc_dynamic_params(funds)

        self.assertEqual(source['mode'], 'dynamic')
        # 中位数验证
        nq_returns = sorted([(1 + 0.3 + i * 0.05) ** (1/3) - 1 for i in range(5)])
        expected_nq_return = round(nq_returns[2], 4)  # 中位数
        self.assertAlmostEqual(params['nasdaq_return'], expected_nq_return, places=3)

        nq_vols = sorted([0.20 + i * 0.02 for i in range(5)])
        self.assertAlmostEqual(params['nasdaq_vol'], nq_vols[2], places=3)

    def test_fallback_mode_with_insufficient_funds(self):
        """基金数量不足时应回退到默认参数"""
        funds = [
            {'index_type': '纳斯达克100', 'return_3yr': 0.3, 'volatility': 0.22},
            {'index_type': '标普500', 'return_3yr': 0.15, 'volatility': 0.18},
        ]
        params, source = calc_dynamic_params(funds)
        self.assertEqual(source['mode'], 'fallback')
        self.assertEqual(params['nasdaq_return'], PARAMS_FALLBACK['nasdaq_return'])
        self.assertEqual(params['nasdaq_vol'], PARAMS_FALLBACK['nasdaq_vol'])

    def test_missing_volatility_uses_fallback(self):
        """有收益率但无波动率时，收益率动态、波动率回退"""
        funds = []
        for i in range(5):
            funds.append({
                'index_type': '纳斯达克100',
                'return_3yr': 0.3 + i * 0.05,
                # 无 volatility 字段
            })
        for i in range(4):
            funds.append({
                'index_type': '标普500',
                'return_3yr': 0.2 + i * 0.05,
            })

        params, source = calc_dynamic_params(funds)
        # 收益率是动态的，波动率是回退的 → 混合模式（2个动态 >= 2）
        self.assertEqual(source['mode'], 'dynamic')
        self.assertNotEqual(params['nasdaq_return'], PARAMS_FALLBACK['nasdaq_return'])
        self.assertEqual(params['nasdaq_vol'], PARAMS_FALLBACK['nasdaq_vol'])

    def test_empty_funds(self):
        """空基金列表应完全回退"""
        params, source = calc_dynamic_params([])
        self.assertEqual(source['mode'], 'fallback')
        for k in PARAMS_FALLBACK:
            if k.startswith('_'):
                continue
            self.assertEqual(params[k], PARAMS_FALLBACK[k])

    def test_params_always_complete(self):
        """无论输入如何，返回的参数应包含所有必需字段"""
        funds = []
        params, _ = calc_dynamic_params(funds)
        required_keys = ['nasdaq_return', 'nasdaq_vol', 'sp500_return', 'sp500_vol',
                        'fx_drift', 'fx_vol', 'dividend_yield', 'dividend_tax']
        for k in required_keys:
            self.assertIn(k, params, f"参数应包含 {k}")
            self.assertIsInstance(params[k], (int, float), f"{k} 应为数值")

    def test_source_details_populated(self):
        """source.details 应包含所有4个关键参数的信息"""
        funds = [
            {'index_type': '纳斯达克100', 'return_3yr': 0.3, 'volatility': 0.22},
            {'index_type': '纳斯达克100', 'return_3yr': 0.4, 'volatility': 0.25},
            {'index_type': '纳斯达克100', 'return_3yr': 0.35, 'volatility': 0.23},
            {'index_type': '标普500', 'return_3yr': 0.2, 'volatility': 0.18},
            {'index_type': '标普500', 'return_3yr': 0.15, 'volatility': 0.16},
            {'index_type': '标普500', 'return_3yr': 0.18, 'volatility': 0.17},
        ]
        _, source = calc_dynamic_params(funds)
        for k in ['nasdaq_return', 'nasdaq_vol', 'sp500_return', 'sp500_vol']:
            self.assertIn(k, source['details'])
            self.assertIn('value', source['details'][k])
            self.assertIn('source', source['details'][k])

    def test_negative_return_handled(self):
        """负收益率的基金应被正确处理"""
        funds = [
            {'index_type': '纳斯达克100', 'return_3yr': -0.3, 'volatility': 0.22},
            {'index_type': '纳斯达克100', 'return_3yr': -0.2, 'volatility': 0.25},
            {'index_type': '纳斯达克100', 'return_3yr': -0.1, 'volatility': 0.23},
        ]
        params, source = calc_dynamic_params(funds)
        # 负收益年化后仍为负
        self.assertLess(params['nasdaq_return'], 0)


if __name__ == '__main__':
    unittest.main()
