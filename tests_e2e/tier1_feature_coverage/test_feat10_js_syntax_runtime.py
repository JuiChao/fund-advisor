"""Tier 1 Feature 10: JavaScript Syntax & Runtime Integrity Tests."""
import re
import subprocess
import unittest
from tests_e2e.e2e_common import APP_JS, SIM_WORKER_JS, load_index_soup, load_app_js, PROJECT_ROOT


class TestJavaScriptSyntaxRuntime(unittest.TestCase):
    """Verifies JavaScript syntax via Node.js compiler and DOM coupling safety."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.app_code = load_app_js()

    def test_node_compile_app_js(self):
        """TC 10.1: Run node -c public/js/app.js and verify exit code 0."""
        res = subprocess.run(
            ["node", "-c", str(APP_JS)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(res.returncode, 0, f"node -c app.js failed:\n{res.stderr}")

    def test_node_compile_sim_worker_js(self):
        """TC 10.2: Run node -c public/js/sim-worker.js and verify exit code 0."""
        res = subprocess.run(
            ["node", "-c", str(SIM_WORKER_JS)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(res.returncode, 0, f"node -c sim-worker.js failed:\n{res.stderr}")

    def test_iife_modular_architecture(self):
        """TC 10.3: Verify modular IIFE architecture in app.js."""
        self.assertIn("const App = (() => {", self.app_code, "app.js must be encapsulated inside an IIFE")

    def test_worker_fallback_calculator_exists(self):
        """TC 10.4: Verify localSimulatePortfolio exists for client-side worker degradation."""
        self.assertIn("localSimulatePortfolio", self.app_code,
                      "app.js must define localSimulatePortfolio for browser environments lacking Worker support")

    def test_critical_dom_selector_coupling(self):
        """TC 10.5: Verify critical DOM IDs targeted by getElementById in app.js exist in index.html."""
        # Extract getElementById calls
        matches = re.findall(r"getElementById\(['\"]([a-zA-Z0-9_\-]+)['\"]\)", self.app_code)
        unique_ids = sorted(list(set(matches)))
        self.assertGreater(len(unique_ids), 30, "app.js must reference multiple DOM IDs")

        # Check critical IDs (allowing quota-bulletin-* aliasing)
        critical_ids = [
            "rank-table", "rank-filter", "class-filter", "quota-filter",
            "pf-m", "pf-y", "btn-pf", "chart-efficient-frontier",
            "sim-m", "sim-y", "btn-sim", "sim-result", "ch-sim",
            "hero-quant-ticker", "footer-us-market-status"
        ]
        for cid in critical_ids:
            el = self.soup.find(id=cid)
            self.assertIsNotNone(el, f"Critical ID '{cid}' used in app.js must exist in index.html")


if __name__ == "__main__":
    unittest.main()
