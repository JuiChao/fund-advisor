"""Tier 1 Feature 4: 5,000-Run Monte Carlo Wealth Simulator Tests."""
import unittest
from tests_e2e.e2e_common import load_index_soup, SIM_WORKER_JS


class TestMonteCarloSimulator(unittest.TestCase):
    """Verifies the DOM elements, parameter controls, and worker setup for #simulator."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()

    def test_preset_buttons_and_multi_select_trigger(self):
        """TC 4.1: Verify strategy preset chips and multi-select dropdown trigger."""
        preset_btns = self.soup.find_all(class_="btn-sim-preset")
        self.assertGreaterEqual(len(preset_btns), 5, "Must have at least 5 preset portfolio buttons in simulator")
        presets = [b.get("data-preset") for b in preset_btns]
        for p in ["risk_parity", "max_sharpe", "balanced", "aggressive", "low_fee"]:
            self.assertIn(p, presets, f"Preset '{p}' must be available")

        trigger = self.soup.find(id="sim-sel-trigger")
        self.assertIsNotNone(trigger, "#sim-sel-trigger must exist")
        dropdown = self.soup.find(id="sim-sel-dropdown")
        self.assertIsNotNone(dropdown, "#sim-sel-dropdown must exist")

    def test_multi_select_search_and_actions(self):
        """TC 4.2: Verify fund search input, select all, clear all, and list container."""
        search = self.soup.find(id="sim-sel-search")
        self.assertIsNotNone(search, "#sim-sel-search input must exist")
        sel_all = self.soup.find(id="sim-sel-all")
        self.assertIsNotNone(sel_all, "#sim-sel-all button must exist")
        sel_clear = self.soup.find(id="sim-sel-clear")
        self.assertIsNotNone(sel_clear, "#sim-sel-clear button must exist")
        sel_list = self.soup.find(id="sim-sel-list")
        self.assertIsNotNone(sel_list, "#sim-sel-list must exist")

    def test_parameter_sliders_and_weights_container(self):
        """TC 4.3: Verify budget and year range inputs and custom weights container."""
        m_slider = self.soup.find(id="sim-m")
        self.assertIsNotNone(m_slider, "Monthly budget input #sim-m must exist")
        self.assertEqual(m_slider.get("min"), "500")
        self.assertEqual(m_slider.get("max"), "10000")

        y_slider = self.soup.find(id="sim-y")
        self.assertIsNotNone(y_slider, "Horizon years input #sim-y must exist")
        self.assertEqual(y_slider.get("min"), "5")
        self.assertEqual(y_slider.get("max"), "30")

        weights_box = self.soup.find(id="sim-weights-container")
        self.assertIsNotNone(weights_box, "#sim-weights-container must exist")
        weights_list = self.soup.find(id="sim-weights-list")
        self.assertIsNotNone(weights_list, "#sim-weights-list must exist")

    def test_smart_dynamic_dca_controls(self):
        """TC 4.4: Verify Smart Dynamic DCA switch, panel, and sensitivity options."""
        toggle = self.soup.find(id="sim-smart-toggle")
        self.assertIsNotNone(toggle, "Checkbox #sim-smart-toggle must exist")
        panel = self.soup.find(id="sim-smart-panel")
        self.assertIsNotNone(panel, "#sim-smart-panel must exist")
        sens_tabs = self.soup.find(id="sim-sens-tabs")
        self.assertIsNotNone(sens_tabs, "#sim-sens-tabs container must exist")
        sens_btns = [b.get("data-sens") for b in sens_tabs.find_all("button")]
        for s in ["conservative", "standard", "aggressive"]:
            self.assertIn(s, sens_btns, f"Sensitivity option '{s}' must exist")
        recom_budget = self.soup.find(id="vg-recom-budget")
        self.assertIsNotNone(recom_budget, "#vg-recom-budget element must exist")

    def test_run_button_output_cards_and_worker(self):
        """TC 4.5: Verify run button, result container, ladder canvas, and worker file."""
        btn_sim = self.soup.find(id="btn-sim")
        self.assertIsNotNone(btn_sim, "Execute button #btn-sim must exist")
        result_box = self.soup.find(id="sim-result")
        self.assertIsNotNone(result_box, "Output container #sim-result must exist")
        canvas = self.soup.find(id="ch-sim")
        self.assertIsNotNone(canvas, "<canvas id='ch-sim'> must exist for probability ladder chart")

        # Verify sim-worker.js file exists and contains onmessage handler
        self.assertTrue(SIM_WORKER_JS.exists(), "public/js/sim-worker.js must exist")
        with open(SIM_WORKER_JS, "r", encoding="utf-8") as f:
            worker_code = f.read()
        self.assertIn("onmessage", worker_code, "sim-worker.js must define onmessage event handler")
        self.assertIn("postMessage", worker_code, "sim-worker.js must return results via postMessage")


if __name__ == "__main__":
    unittest.main()
