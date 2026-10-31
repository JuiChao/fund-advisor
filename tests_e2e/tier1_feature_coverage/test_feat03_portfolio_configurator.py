"""Tier 1 Feature 3: MPT Asset Allocation Portfolio Configurator Tests."""
import unittest
from tests_e2e.e2e_common import load_index_soup, load_algo_data


class TestPortfolioConfigurator(unittest.TestCase):
    """Verifies the DOM elements, controls, and configuration structures of #portfolio."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.algo = load_algo_data()

    def test_inputs_and_stepper_controls(self):
        """TC 3.1: Verify monthly budget (#pf-m) and horizon (#pf-y) sliders, badges, and steppers."""
        budget_slider = self.soup.find(id="pf-m")
        self.assertIsNotNone(budget_slider, "Monthly budget slider #pf-m must exist")
        self.assertEqual(budget_slider.get("min"), "500")
        self.assertEqual(budget_slider.get("max"), "10000")

        horizon_slider = self.soup.find(id="pf-y")
        self.assertIsNotNone(horizon_slider, "Investment horizon slider #pf-y must exist")
        self.assertEqual(horizon_slider.get("min"), "5")
        self.assertEqual(horizon_slider.get("max"), "30")

        # Stepper buttons
        steppers = self.soup.find_all(class_="input-stepper-btn")
        self.assertGreaterEqual(len(steppers), 4, "Must have stepper increment/decrement buttons for inputs")

        # Badges
        self.assertIsNotNone(self.soup.find(id="pf-mv-badge"), "#pf-mv-badge must exist")
        self.assertIsNotNone(self.soup.find(id="pf-yv-badge"), "#pf-yv-badge must exist")

    def test_efficient_frontier_container_and_canvas(self):
        """TC 3.2: Verify Efficient Frontier card, toggle trigger, and Chart.js canvas."""
        card = self.soup.find(id="quant-frontier-card")
        self.assertIsNotNone(card, "#quant-frontier-card must exist")
        toggle = self.soup.find(id="quant-frontier-toggle")
        self.assertIsNotNone(toggle, "#quant-frontier-toggle must exist")
        canvas = self.soup.find(id="chart-efficient-frontier")
        self.assertIsNotNone(canvas, "<canvas id='chart-efficient-frontier'> must exist")

    def test_frontier_inspector_and_risk_bars(self):
        """TC 3.3: Verify interactive slider (#frontier-range-slider) and risk decomposition bars."""
        inspector = self.soup.find(id="frontier-inspector-card")
        self.assertIsNotNone(inspector, "#frontier-inspector-card must exist")
        slider = self.soup.find(id="frontier-range-slider")
        self.assertIsNotNone(slider, "#frontier-range-slider range input must exist")
        self.assertEqual(slider.get("min"), "0")
        self.assertEqual(slider.get("max"), "100")

        # Risk and capital split bars
        self.assertIsNotNone(self.soup.find(id="f-cap-nq"), "#f-cap-nq capital split bar must exist")
        self.assertIsNotNone(self.soup.find(id="f-cap-sp"), "#f-cap-sp capital split bar must exist")
        self.assertIsNotNone(self.soup.find(id="f-risk-nq"), "#f-risk-nq risk contribution bar must exist")
        self.assertIsNotNone(self.soup.find(id="f-risk-sp"), "#f-risk-sp risk contribution bar must exist")

    def test_category_filters_and_strategy_matrix(self):
        """TC 3.4: Verify strategy category filter pills and quantitative matrix tbody."""
        cat_filter = self.soup.find(id="pf-category-filter")
        self.assertIsNotNone(cat_filter, "#pf-category-filter must exist")
        categories = [btn.get("data-category") for btn in cat_filter.find_all("button")]
        self.assertIn("ALL", categories)
        self.assertIn("traditional", categories)
        self.assertIn("quant", categories)

        matrix_tbody = self.soup.find(id="quant-matrix-tbody")
        self.assertIsNotNone(matrix_tbody, "#quant-matrix-tbody must exist for rendering strategy comparisons")

        # Verify strategy definitions in algorithm.json
        strategies = self.algo.get("strategies", [])
        self.assertGreaterEqual(len(strategies), 5, "algorithm.json must define at least 5 strategies")
        keys = [s["key"] for s in strategies]
        self.assertIn("risk_parity", keys)
        self.assertIn("max_sharpe", keys)
        self.assertIn("balanced", keys)

    def test_stress_test_section_and_scenarios(self):
        """TC 3.5: Verify historical crisis stress testing section, scenario tabs, canvas, and table."""
        stress_sec = self.soup.find(id="stress-test-section")
        self.assertIsNotNone(stress_sec, "#stress-test-section must exist")
        tabs = self.soup.find(id="stress-scenario-tabs")
        self.assertIsNotNone(tabs, "#stress-scenario-tabs must exist")

        scenario_keys = [btn.get("data-scenario") for btn in tabs.find_all("button")]
        for s in ["gfc", "covid", "dotcom", "ratehike"]:
            self.assertIn(s, scenario_keys, f"Scenario tab for '{s}' must exist")

        canvas = self.soup.find(id="chart-stress-test")
        self.assertIsNotNone(canvas, "<canvas id='chart-stress-test'> must exist")
        tbody = self.soup.find(id="stress-test-tbody")
        self.assertIsNotNone(tbody, "#stress-test-tbody must exist")


if __name__ == "__main__":
    unittest.main()
