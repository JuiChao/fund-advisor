#!/usr/bin/env python3
"""
数据校验函数单元测试
测试 scrape.py 的 validate 函数

运行: cd fund-advisor && python -m unittest tests.test_validate -v
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from scraper.scrape import validate


class TestValidate(unittest.TestCase):
    """测试数据校验函数"""

    def test_valid_data_passes(self):
        """合法数据应全部通过"""
        data = {
            'tracking_error': 0.02,
            'scale': 15.5,
            'return_1yr': 0.15,
            'return_3yr': 0.45,
            'mgmt_fee': 0.008,
            'custody_fee': 0.002,
            'morningstar': 4,
        }
        cleaned = validate(data)
        for k, v in data.items():
            self.assertEqual(cleaned[k], v, f"合法字段 {k}={v} 应保留")

    def test_out_of_range_dropped(self):
        """超出范围的数据应被丢弃"""
        data = {
            'tracking_error': 0.5,      # 远超 0.15 上限
            'scale': 9999,              # 远超 1000 上限
            'return_1yr': 10.0,         # 远超 5.0 上限
            'mgmt_fee': 0.1,            # 远超 0.03 上限
        }
        cleaned = validate(data)
        self.assertNotIn('tracking_error', cleaned, "异常跟踪误差应被丢弃")
        self.assertNotIn('scale', cleaned, "异常规模应被丢弃")
        self.assertNotIn('return_1yr', cleaned, "异常收益率应被丢弃")
        self.assertNotIn('mgmt_fee', cleaned, "异常管理费应被丢弃")

    def test_none_values_dropped(self):
        """None 值的校验字段应被丢弃"""
        data = {
            'tracking_error': None,
            'scale': None,
            'morningstar': None,
        }
        cleaned = validate(data)
        self.assertNotIn('tracking_error', cleaned)
        self.assertNotIn('scale', cleaned)
        self.assertNotIn('morningstar', cleaned)

    def test_non_validated_fields_preserved(self):
        """不在校验列表中的字段应原样保留"""
        data = {
            'code': '000001',
            'name': '测试基金',
            'custom_field': '任意值',
        }
        cleaned = validate(data)
        self.assertEqual(cleaned['code'], '000001')
        self.assertEqual(cleaned['name'], '测试基金')
        self.assertEqual(cleaned['custom_field'], '任意值')

    def test_boundary_values(self):
        """边界值应通过校验"""
        data = {
            'tracking_error': 0.001,    # 下界
            'scale': 1000,              # 上界
            'return_1yr': -0.8,         # 下界
            'morningstar': 0,           # 下界
            'morningstar_5': 5,         # 上界
        }
        cleaned = validate(data)
        self.assertEqual(cleaned['tracking_error'], 0.001)
        self.assertEqual(cleaned['scale'], 1000)
        self.assertEqual(cleaned['return_1yr'], -0.8)

    def test_empty_dict(self):
        """空字典不应报错"""
        cleaned = validate({})
        self.assertEqual(cleaned, {})


if __name__ == '__main__':
    unittest.main()
