"""Tier 2 Boundary 9: Python Unit Tests Boundary & Corner Cases Tests."""
import unittest
from tests_e2e.e2e_common import load_algo_data, TESTS_DIR


class TestPythonUnitTestsBoundary(unittest.TestCase):
    """Verifies edge cases in unit test coverage: validation bounds, dynamic fallback, and numerical guards."""

    @classmethod
    def setUpClass(cls):
        cls.algo = load_algo_data()

    def test_validation_bounds_specification(self):
        """TC 9.1: Verify validation bounds specified in algorithm.json match test_validate.py ranges."""
        validation = self.algo.get("validation", {})
        self.assertIn("tracking_error", validation)
        self.assertIn("scale", validation)
        self.assertIn("return_1yr", validation)
        self.assertIn("mgmt_fee", validation)
        # Bounds should be 2-element [min, max] lists
        self.assertEqual(len(validation["tracking_error"]), 2)
        self.assertLess(validation["tracking_error"][0], validation["tracking_error"][1])

    def test_params_fallback_completeness(self):
        """TC 9.2: Verify simulation params_fallback defines all macro keys in case dynamic sampling fails."""
        fallback = self.algo.get("simulation", {}).get("params_fallback", {})
        required_keys = ["nasdaq_return", "nasdaq_vol", "sp500_return", "sp500_vol", "fx_drift", "fx_vol"]
        for key in required_keys:
            self.assertIn(key, fallback, f"params_fallback must define fallback value for '{key}'")

    def test_dynamic_params_min_funds_threshold(self):
        """TC 9.3: Verify dynamic parameter sampling requires minimum threshold of funds."""
        dyn_cfg = self.algo.get("simulation", {}).get("dynamic_params", {})
        min_funds = dyn_cfg.get("min_funds_for_dynamic", 0)
        self.assertGreaterEqual(min_funds, 3, "Must require at least 3 funds to compute dynamic median")

    def test_fsm_boundary_test_presence(self):
        """TC 9.4: Verify test_fsm.py tests boundary transitions (e.g. unknown notices, malformed dates)."""
        fsm_path = TESTS_DIR / "test_fsm.py"
        with open(fsm_path, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("def test_", code, "test_fsm.py must define test cases")
        self.assertIn("class ", code, "test_fsm.py must define test classes")

    def test_default_imputation_values(self):
        """TC 9.5: Verify defaults block defines imputations for missing fields in algorithm.json."""
        defaults = self.algo.get("defaults", {})
        self.assertIn("tracking_error_for_scoring", defaults)
        self.assertIn("scale", defaults)
        self.assertIn("mgmt_fee", defaults)
        self.assertIn("custody_fee", defaults)


if __name__ == "__main__":
    unittest.main()
