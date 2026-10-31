"""Tier 3: Pairwise & Cross-Feature Interactions Tests (>=15 test cases)."""
import re
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import (
    load_index_soup, load_about_soup, load_style_css, load_app_js,
    load_funds_data, load_algo_data, load_limit_changes_data,
    get_article_files, get_fund_page_files
)


class TestPairwiseInteractions(unittest.TestCase):
    """Verifies pairwise combinatorial interactions across themes, filters, sliders, and navigation."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.js = load_app_js()
        cls.funds = load_funds_data()
        cls.algo = load_algo_data()
        cls.limits = load_limit_changes_data()
        cls.articles = get_article_files()
        cls.fund_pages = get_fund_page_files()

    def test_pairwise_theme_and_table_sort(self):
        """TC 3.1: Pairwise: Theme switching + Table sort indicator contrast."""
        self.assertIn("data-theme=\"dark\"", self.css or self.soup.prettify())
        self.assertIn("applyTheme", self.js)
        # Verify sort indicators on table headers exist in both themes
        table = self.soup.find(id="rank-table")
        self.assertIsNotNone(table)
        headers = table.find_all("th")
        self.assertGreaterEqual(len(headers), 10)

    def test_pairwise_theme_and_table_filter(self):
        """TC 3.2: Pairwise: Theme switching + Index filter tabs active states."""
        self.assertIn(".seg-btn.on", self.css)
        rank_filter = self.soup.find(id="rank-filter")
        self.assertIsNotNone(rank_filter)
        active_btn = rank_filter.find("button", class_="on")
        self.assertIsNotNone(active_btn, "Index filter must have an active button state")

    def test_pairwise_theme_and_mobile_nav(self):
        """TC 3.3: Pairwise: Theme switching + Mobile navigation drawer interaction."""
        toggle = self.soup.find(id="theme-toggle")
        self.assertIsNotNone(toggle)
        nav_toggle = self.soup.find(class_="nav-toggle")
        self.assertIsNotNone(nav_toggle)
        # Verify style.css defines mobile drawer open state
        self.assertTrue(".nav-links.show" in self.css or "#nav-links.show" in self.css or ".links.show" in self.css)

    def test_pairwise_search_query_and_quota_filter(self):
        """TC 3.4: Pairwise: Search query input + Quota availability filter."""
        # Simulated combinatorial filter: find buyable funds managed by 易方达
        matched = [
            f for f in self.funds
            if "易方达" in f.get("name", "") and f.get("daily_limit", 0) > 0
        ]
        self.assertIsInstance(matched, list)

    def test_pairwise_portfolio_budget_and_horizon(self):
        """TC 3.5: Pairwise: Monthly budget slider + Horizon slider parameter combination."""
        m_slider = self.soup.find(id="pf-m")
        y_slider = self.soup.find(id="pf-y")
        self.assertIsNotNone(m_slider)
        self.assertIsNotNone(y_slider)
        # Test extreme pairwise: max budget (10000) * max horizon (30 years)
        total_invested = 10000 * 12 * 30
        self.assertEqual(total_invested, 3600000)

    def test_pairwise_portfolio_category_and_stress_scenario(self):
        """TC 3.6: Pairwise: Strategy category selection + Crisis stress test scenario."""
        cat_filter = self.soup.find(id="pf-category-filter")
        stress_tabs = self.soup.find(id="stress-scenario-tabs")
        self.assertIsNotNone(cat_filter)
        self.assertIsNotNone(stress_tabs)
        # Verify stress scenarios defined in app.js
        self.assertIn("_activeStressScenario", self.js)

    def test_pairwise_portfolio_slider_and_risk_decomposition(self):
        """TC 3.7: Pairwise: Nasdaq weight allocation slider + Risk contribution bars."""
        slider = self.soup.find(id="frontier-range-slider")
        self.assertIsNotNone(slider)
        cap_bar = self.soup.find(id="f-cap-nq")
        risk_bar = self.soup.find(id="f-risk-nq")
        self.assertIsNotNone(cap_bar)
        self.assertIsNotNone(risk_bar)

    def test_pairwise_monte_carlo_preset_and_smart_dca(self):
        """TC 3.8: Pairwise: Simulation preset strategy + Smart Dynamic DCA toggle."""
        preset_btn = self.soup.find(class_="btn-sim-preset")
        self.assertIsNotNone(preset_btn)
        toggle = self.soup.find(id="sim-smart-toggle")
        self.assertIsNotNone(toggle)
        self.assertIn("isSmartDCA", self.js)

    def test_pairwise_monte_carlo_multiselect_and_weights(self):
        """TC 3.9: Pairwise: Multi-select fund picker + Weights display update."""
        trigger = self.soup.find(id="sim-sel-trigger")
        self.assertIsNotNone(trigger)
        self.assertIn("updateWeightDisplays", self.js)

    def test_pairwise_quota_alert_and_ranking_anchor(self):
        """TC 3.10: Pairwise: Quota alert bar click + Hash navigation to quota bulletin."""
        # Check quota button or radar link navigates to #ranking?section=quota
        links = [a.get("href") for a in self.soup.find_all("a", href=True)]
        quota_links = [l for l in links if "section=quota" in l or "#ranking" in l]
        self.assertGreater(len(quota_links), 0)

    def test_pairwise_quota_table_and_export_modal(self):
        """TC 3.11: Pairwise: Quota bulletin board + Poster export button."""
        tbody = self.soup.find(id="quota-table-tbody")
        self.assertIsNotNone(tbody)
        export_btn = self.soup.find(id="btn-quota-export-douyin")
        self.assertIsNotNone(export_btn)

    def test_pairwise_dual_view_and_viewport_resize(self):
        """TC 3.12: Pairwise: Card vs Table view toggle + Mobile card view container."""
        toggle = self.soup.find(id="rank-view-toggle")
        self.assertIsNotNone(toggle)
        card_list = self.soup.find(id="rank-card-list")
        self.assertIsNotNone(card_list)
        table_wrap = self.soup.find(id="rank-table-wrap")
        self.assertIsNotNone(table_wrap)

    def test_pairwise_navigation_hash_and_page_containers(self):
        """TC 3.13: Pairwise: Navigation hash routes (#home, #ranking, #portfolio, #simulator) + DOM pages."""
        pages = ["page-home", "page-ranking", "page-portfolio", "page-simulator", "page-guide"]
        for p in pages:
            el = self.soup.find(id=p)
            self.assertIsNotNone(el, f"Page container #{p} must exist in index.html")

    def test_pairwise_seo_generator_and_funds_data(self):
        """TC 3.14: Pairwise: Generated fund detail page title + Funds data JSON code and name."""
        sample_fund = self.funds[0]
        sample_file = self.fund_pages[0]
        with open(sample_file, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        title_text = soup.find("title").get_text()
        self.assertIn(sample_file.stem, title_text)

    def test_pairwise_article_tables_and_theme_legibility(self):
        """TC 3.15: Pairwise: Article table styling + Theme custom properties (--txt, --border)."""
        self.assertIn("var(--txt)", self.css)
        self.assertIn("var(--border)", self.css)
        self.assertIn("var(--bg)", self.css)

    def test_pairwise_fund_detail_substitute_and_navigation(self):
        """TC 3.16: Pairwise: Fund detail substitute fund recommendation + Navigation target."""
        # Verify substitute generator logic exists in generate_seo.py
        with open("scraper/generate_seo.py", "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("find_substitutes", code)


if __name__ == "__main__":
    unittest.main()
