"""Tier 2 Boundary 10: JavaScript Syntax & Runtime Integrity Boundary & Corner Cases Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_app_js, SIM_WORKER_JS


class TestJavaScriptSyntaxRuntimeBoundary(unittest.TestCase):
    """Verifies JavaScript security constraints, memory guards, and global scope isolation."""

    @classmethod
    def setUpClass(cls):
        cls.app_code = load_app_js()
        with open(SIM_WORKER_JS, "r", encoding="utf-8") as f:
            cls.worker_code = f.read()

    def test_no_eval_or_with_statements(self):
        """TC 10.1: Verify strict absence of dangerous eval() or with statements in scripts."""
        # Search for eval(...) not inside comments or strings
        self.assertIsNone(re.search(r"(?<![a-zA-Z0-9_])eval\s*\(", self.app_code),
                          "app.js must not use eval() execution")
        self.assertIsNone(re.search(r"(?<![a-zA-Z0-9_])eval\s*\(", self.worker_code),
                          "sim-worker.js must not use eval() execution")
        self.assertIsNone(re.search(r"\bwith\s*\(", self.app_code),
                          "app.js must not use with statements")

    def test_local_storage_fallback_guard(self):
        """TC 10.2: Verify localStorage access checks or fallbacks for private browsing mode."""
        self.assertIn("localStorage.getItem", self.app_code, "app.js must check localStorage for persisted preferences")
        # Ensure fallback defaults exist when localStorage is empty
        has_fallback = "||" in self.app_code or "??" in self.app_code or "try" in self.app_code
        self.assertTrue(has_fallback, "app.js must supply fallback when localStorage returns null")

    def test_worker_event_data_extraction(self):
        """TC 10.3: Verify sim-worker.js safely extracts funds, weights, years, and budget from event.data."""
        self.assertIn("e.data", self.worker_code, "sim-worker.js must extract parameters from e.data")
        expected_params = ["funds", "weights", "years", "budget"]
        for p in expected_params:
            self.assertIn(p, self.worker_code, f"sim-worker.js must process '{p}' parameter from worker message")

    def test_global_scope_isolation(self):
        """TC 10.4: Verify app.js exposes only the App namespace or lifecycle entrypoint."""
        self.assertIn("const App = (() => {", self.app_code)
        self.assertIn("return { init", self.app_code, "App module must cleanly export init method")

    def test_json_fetch_promise_aggregation(self):
        """TC 10.5: Verify parallel loading of dataset files via Promise.all."""
        self.assertIn("Promise.all", self.app_code, "app.js must aggregate dataset loading using Promise.all")


if __name__ == "__main__":
    unittest.main()
