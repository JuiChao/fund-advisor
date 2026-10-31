"""Tier 2 Boundary 2: Matrix Table Boundary & Corner Cases Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_funds_data, load_algo_data


class TestMatrixTableBoundary(unittest.TestCase):
    """Verifies edge cases in table data distributions, boundaries, and filter math."""

    @classmethod
    def setUpClass(cls):
        cls.funds = load_funds_data()
        cls.algo = load_algo_data()

    def test_tracking_error_boundaries(self):
        """TC 2.1: Verify tracking error distribution remains within realistic quant bounds."""
        tes = [f["tracking_error"] for f in self.funds if f.get("tracking_error") is not None]
        self.assertGreater(len(tes), 40, "At least 40 funds must have tracking error data")
        min_te = min(tes)
        max_te = max(tes)
        self.assertGreaterEqual(min_te, 0.001, f"Minimum tracking error ({min_te}) must be >= 0.1%")
        self.assertLessEqual(max_te, 0.15, f"Maximum tracking error ({max_te}) must be <= 15%")

    def test_scale_distribution_boundaries(self):
        """TC 2.2: Verify catalog covers both emerging small-scale and established giant funds."""
        scales = [f["scale"] for f in self.funds if f.get("scale") is not None]
        min_scale = min(scales)
        max_scale = max(scales)
        self.assertLess(min_scale, 5.0, f"Expected small-cap emerging funds under 5亿, found min={min_scale}亿")
        self.assertGreater(max_scale, 30.0, f"Expected large flagship funds over 30亿, found max={max_scale}亿")

    def test_zero_match_filter_handling(self):
        """TC 2.3: Verify filtering on non-existent share class yields 0 matches without exception."""
        non_existent_class = [f for f in self.funds if f.get("share_class") == "XYZ"]
        self.assertEqual(len(non_existent_class), 0, "Non-existent share class must yield empty list")

    def test_search_string_escaping_resilience(self):
        """TC 2.4: Test substring search matching resilience against special characters."""
        # Simulated search filter
        def search_funds(query):
            q = query.strip().lower()
            return [
                f for f in self.funds
                if q in f.get("code", "").lower() or q in f.get("name", "").lower()
            ]

        # Empty query returns full catalog
        self.assertEqual(len(search_funds("")), len(self.funds))
        # Whitespace query returns full catalog
        self.assertEqual(len(search_funds("   ")), len(self.funds))
        # Known code search
        self.assertGreater(len(search_funds("000834")), 0)
        # Search query with regex special chars shouldn't crash substring match
        res_regex = search_funds("[0-9]+")
        self.assertEqual(len(res_regex), 0)

    def test_total_fee_boundaries(self):
        """TC 2.5: Verify total fee (mgmt + custody + sales) remains within statutory limits."""
        for f in self.funds:
            mgmt = f.get("mgmt_fee", 0.0) or 0.0
            custody = f.get("custody_fee", 0.0) or 0.0
            sales = f.get("sales_fee", 0.0) or 0.0
            total_fee = mgmt + custody + sales
            self.assertGreaterEqual(total_fee, 0.003, f"Fund {f['code']} total fee {total_fee} suspiciously low (<0.3%)")
            self.assertLessEqual(total_fee, 0.025, f"Fund {f['code']} total fee {total_fee} exceeds 2.5% max limit")


if __name__ == "__main__":
    unittest.main()
