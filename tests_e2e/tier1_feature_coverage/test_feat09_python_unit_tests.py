"""Tier 1 Feature 9: Python Unit Test Suite Tests."""
import unittest
from tests_e2e.e2e_common import TESTS_DIR


class TestPythonUnitTests(unittest.TestCase):
    """Verifies the presence, discoverability, and coverage of the existing 94 unit tests."""

    @classmethod
    def setUpClass(cls):
        cls.test_files = sorted(TESTS_DIR.glob("test_*.py"))
        cls.suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), pattern="test_*.py")

    def test_7_test_suites_exist(self):
        """TC 9.1: Verify all 7 core test files exist in tests/ directory."""
        expected_files = [
            "test_algorithm.py",
            "test_cdc.py",
            "test_dynamic_params.py",
            "test_fsm.py",
            "test_limit_tracker.py",
            "test_validate.py",
            "test_verify_quotas.py"
        ]
        found_names = [f.name for f in self.test_files]
        for name in expected_files:
            self.assertIn(name, found_names, f"Test file {name} must exist in tests/")

    def test_94_test_cases_discovered(self):
        """TC 9.2: Verify test loader discovers exactly 94 test cases in tests/."""
        count = self.suite.countTestCases()
        self.assertEqual(count, 94, f"Expected 94 unit tests, discovered {count}")

    def test_algorithm_test_coverage(self):
        """TC 9.3: Verify test_algorithm.py covers scoring, MPT, and Monte Carlo mathematics."""
        algo_file = TESTS_DIR / "test_algorithm.py"
        with open(algo_file, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("score_fund", code)
        self.assertIn("calc_risk_parity_weights", code)
        self.assertIn("simulate_portfolio", code)

    def test_fsm_and_quota_verification_coverage(self):
        """TC 9.4: Verify test_fsm.py and test_verify_quotas.py validate quota state transitions."""
        fsm_file = TESTS_DIR / "test_fsm.py"
        with open(fsm_file, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertTrue("parse_notice" in code or "transition" in code or "State" in code or "limit" in code)

        quota_file = TESTS_DIR / "test_verify_quotas.py"
        with open(quota_file, "r", encoding="utf-8") as f:
            quota_code = f.read()
        self.assertTrue("quota" in quota_code or "limit" in quota_code)

    def test_data_validation_coverage(self):
        """TC 9.5: Verify test_validate.py checks schema consistency and range constraints."""
        validate_file = TESTS_DIR / "test_validate.py"
        with open(validate_file, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("validate", code)
        self.assertIn("tracking_error", code)
        self.assertIn("scale", code)


if __name__ == "__main__":
    unittest.main()
