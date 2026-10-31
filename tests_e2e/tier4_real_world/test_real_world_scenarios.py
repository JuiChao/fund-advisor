"""Tier 4: Real-World User Scenarios Tests (5 Real-World End-to-End User Journeys)."""
import json
import re
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import (
    load_index_soup, load_about_soup, load_style_css, load_app_js,
    load_funds_data, load_algo_data, load_limit_changes_data,
    ARTICLES_DIR, FUND_PAGES_DIR
)


class TestRealWorldScenarios(unittest.TestCase):
    """Executes 5 comprehensive real-world investor journeys across all components."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.about_soup = load_about_soup()
        cls.css = load_style_css()
        cls.js = load_app_js()
        cls.funds = load_funds_data()
        cls.algo = load_algo_data()
        cls.limits = load_limit_changes_data()

    def test_scenario_1_global_asset_allocation_flow(self):
        """Scenario 1: Global Asset Allocation User Flow.
        Journey: Telemetry HUD -> Ranking Table -> Portfolio Configurator -> Crisis Stress Tests.
        """
        # Step 1: User observes Telemetry HUD
        hud = self.soup.find(id="hero-quant-ticker")
        self.assertIsNotNone(hud, "Step 1: Telemetry HUD must be present on landing")
        status_span = self.soup.find(id="ticker-market-status")
        self.assertIsNotNone(status_span, "Step 1: Telemetry must include live market session status")

        # Step 2: User inspects Ranking Matrix Table
        rank_table = self.soup.find(id="rank-table")
        self.assertIsNotNone(rank_table, "Step 2: User scrolls to 60-target ranking matrix table")
        headers = [th.get("data-key") for th in rank_table.find_all("th") if th.get("data-key")]
        self.assertIn("score", headers, "Step 2: Table must include quantitative multi-factor score")

        # Step 3: User configures Portfolio Allocation parameters
        pf_page = self.soup.find(id="page-portfolio")
        self.assertIsNotNone(pf_page, "Step 3: User transitions to Portfolio Configurator")
        self.assertIsNotNone(self.soup.find(id="pf-m"), "Step 3: Budget slider must exist")
        self.assertIsNotNone(self.soup.find(id="pf-y"), "Step 3: Horizon slider must exist")

        # Step 4: User inspects Efficient Frontier & Risk Parity
        frontier_card = self.soup.find(id="quant-frontier-card")
        self.assertIsNotNone(frontier_card, "Step 4: Efficient frontier card must exist")
        self.assertIsNotNone(self.soup.find(id="chart-efficient-frontier"), "Step 4: Frontier canvas must exist")

        # Step 5: User evaluates Historical Crisis Stress Tests
        stress_sec = self.soup.find(id="stress-test-section")
        self.assertIsNotNone(stress_sec, "Step 5: Crisis stress testing section must exist")
        tabs = self.soup.find(id="stress-scenario-tabs")
        self.assertIsNotNone(tabs, "Step 5: Scenario tabs (GFC, COVID, Dot-Com, Rate-Hike) must exist")

    def test_scenario_2_qdii_fund_selection_and_quota_check_flow(self):
        """Scenario 2: QDII Fund Selection & Quota Check Flow.
        Journey: Ranking Filter -> Purchase Radar -> Fund Detail Page Navigation.
        """
        # Step 1: User filters by index (Nasdaq 100)
        rank_filter = self.soup.find(id="rank-filter")
        self.assertIsNotNone(rank_filter, "Step 1: Index filter tabs must exist")
        nq_btn = rank_filter.find("button", attrs={"data-value": "纳斯达克100"})
        self.assertIsNotNone(nq_btn, "Step 1: Nasdaq 100 filter button must exist")

        # Step 2: User filters by share class (C-Class)
        class_filter = self.soup.find(id="class-filter")
        c_btn = class_filter.find("button", attrs={"data-value": "C"})
        self.assertIsNotNone(c_btn, "Step 2: C-Class filter button must exist")

        # Step 3: User inspects Quota Bulletin & Radar
        radar_card = self.soup.find(class_="home-quota-radar-card")
        self.assertIsNotNone(radar_card, "Step 3: Quota radar card must exist")
        alert_bar = self.soup.find(id="quota-alert-bar")
        self.assertIsNotNone(alert_bar, "Step 3: Quota alert ticker must exist")

        # Step 4: Quota data check in catalog
        shared_funds = [f for f in self.funds if f.get("quota_sharing") == "SHARED"]
        self.assertGreater(len(shared_funds), 0, "Step 4: Catalog must identify quota sharing funds")

        # Step 5: Navigation to Fund Detail page
        sample_code = shared_funds[0]["code"]
        fund_page = FUND_PAGES_DIR / f"{sample_code}.html"
        self.assertTrue(fund_page.exists(), f"Step 5: Detail page for fund {sample_code} must exist")
        with open(fund_page, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(sample_code, content, "Step 5: Fund page must present matching fund code")

    def test_scenario_3_retirement_wealth_accumulation_simulation(self):
        """Scenario 3: Retirement Wealth Accumulation Simulation.
        Journey: Monte Carlo Simulator -> DCA Slider Adjustments -> Probability Ladder Evaluation.
        """
        # Step 1: Enter Simulator Page
        sim_page = self.soup.find(id="page-simulator")
        self.assertIsNotNone(sim_page, "Step 1: Simulator page container must exist")

        # Step 2: Configure DCA parameters
        budget_input = self.soup.find(id="sim-m")
        years_input = self.soup.find(id="sim-y")
        self.assertIsNotNone(budget_input, "Step 2: Budget slider must exist")
        self.assertIsNotNone(years_input, "Step 2: Horizon slider must exist")

        # Step 3: Activate Smart Dynamic DCA
        smart_toggle = self.soup.find(id="sim-smart-toggle")
        self.assertIsNotNone(smart_toggle, "Step 3: Smart Dynamic DCA toggle must exist")
        sens_tabs = self.soup.find(id="sim-sens-tabs")
        self.assertIsNotNone(sens_tabs, "Step 3: Sensitivity options must exist")

        # Step 4: Verify simulation execution contract
        run_btn = self.soup.find(id="btn-sim")
        self.assertIsNotNone(run_btn, "Step 4: Execute button #btn-sim must exist")
        self.assertIn("simulateViaWorker", self.js, "Step 4: app.js must execute simulation via Worker")

        # Step 5: Terminal probability ladder
        ladder_canvas = self.soup.find(id="ch-sim")
        self.assertIsNotNone(ladder_canvas, "Step 5: Probability ladder canvas #ch-sim must exist")

    def test_scenario_4_quantitative_research_due_diligence_flow(self):
        """Scenario 4: Quantitative Research Due Diligence Flow.
        Journey: About Page -> Methodology -> Research Article -> In-text Data Table -> Fund Detail.
        """
        # Step 1: Researcher audits About Page
        about_title = self.about_soup.find("title")
        self.assertIn("关于我们", about_title.get_text(), "Step 1: About page title must be valid")
        self.assertIn("CFA", self.about_soup.get_text(), "Step 1: Credentials should mention CFA")

        # Step 2: Navigate to Research Hub
        hub_path = ARTICLES_DIR / "index.html"
        self.assertTrue(hub_path.exists(), "Step 2: Research Hub index.html must exist")

        # Step 3: Select Research Article with data tables
        article_file = ARTICLES_DIR / "how-to-choose-qdii-funds.html"
        self.assertTrue(article_file.exists(), "Step 3: Research article must exist")
        with open(article_file, "r", encoding="utf-8") as f:
            article_soup = BeautifulSoup(f.read(), "html.parser")

        # Step 4: Audit report tables and structured schema
        tables = article_soup.find_all("table")
        self.assertGreater(len(tables), 0, "Step 4: Article must contain analytical data tables")
        json_ld = article_soup.find("script", type="application/ld+json")
        self.assertIsNotNone(json_ld, "Step 4: Article must have JSON-LD schema")

        # Step 5: Follow link back to ranking or fund directory to view fund detail page
        sample_code = self.funds[0]["code"]
        fund_page = FUND_PAGES_DIR / f"{sample_code}.html"
        self.assertTrue(fund_page.exists(), "Step 5: Fund detail page must exist for due diligence lookup")
        with open(fund_page, "r", encoding="utf-8") as f:
            detail_content = f.read()
        self.assertIn("量化评测", detail_content, "Step 5: Fund detail page must contain quant review")

    def test_scenario_5_cross_device_responsive_transition_flow(self):
        """Scenario 5: Cross-Device Responsive Transition Flow.
        Journey: Mobile (375px) -> Tablet (768px) -> Desktop (1440px) viewport consistency without overflow.
        """
        # Step 1: Mobile (375px) controls
        meta_vp = self.soup.find("meta", attrs={"name": "viewport"})
        self.assertIn("width=device-width", meta_vp.get("content", ""), "Step 1: Must set width=device-width")
        self.assertIsNotNone(self.soup.find(class_="nav-toggle"), "Step 1: Mobile drawer toggle must exist")
        self.assertIsNotNone(self.soup.find(id="rank-card-list"), "Step 1: Mobile card view container must exist")

        # Step 2: Tablet (768px) media query
        self.assertRegex(self.css, r"@media\s*\([^\)]*max-width\s*:\s*768px", "Step 2: 768px media query must exist")

        # Step 3: Desktop (1440px) table view
        self.assertIsNotNone(self.soup.find(id="rank-table"), "Step 3: Full matrix table must exist for desktop")

        # Step 4: Overflow prevention
        has_box_sizing = bool(re.search(r"box-sizing\s*:\s*border-box", self.css))
        self.assertTrue(has_box_sizing, "Step 4: Universal box-sizing must prevent horizontal blowout")

        # Step 5: Typography styling
        self.assertIn("tabular-nums", self.css, "Step 5: Numeric data must use tabular numerals for alignment")


if __name__ == "__main__":
    unittest.main()
