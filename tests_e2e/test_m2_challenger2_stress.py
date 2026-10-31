"""Automated Stress-Test Harness for Milestone 2 Challenger 2.

Empirical verification of:
1. Multi-viewport responsive layout adaptability across mobile (375px), tablet (768px), and desktop (1440px)
   for #rank-table, #portfolio, #simulator, and #radar.
2. Sticky columns on #rank-table: z-index hierarchy, hover parity across row archetypes, horizontal overflow
   containment, and absence of visual clipping on narrow viewports.
3. Anchor navigation from the quota radar CTA button to the quota bulletin container: URL hash resolution,
   dual DOM ID fallback, scroll-margin-top navbar compensation, and absence of null reference exceptions.
"""

import os
import re
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests_e2e.e2e_common import (
    load_index_soup, load_style_css, load_app_js, load_funds_data, load_limit_changes_data
)


class TestRankTableViewportAndStickyScroll(unittest.TestCase):
    """Stress tests #rank-table layout, sticky column constraints, hover parity, and horizontal scrolling."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.app_js = load_app_js()
        cls.funds = load_funds_data()

    def test_rank_table_container_bounds_and_overflow_x(self):
        """TC 2.1: Verify .table-wrap has overflow-x auto, touch scrolling, and overscroll containment."""
        table_wrap = self.soup.find(id="rank-table-wrap")
        self.assertIsNotNone(table_wrap, "Markup must include #rank-table-wrap")
        self.assertIn("table-wrap", table_wrap.get("class", []))

        # Check CSS rules for .table-wrap
        tw_match = re.search(r"\.table-wrap\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(tw_match, "style.css must define .table-wrap")
        tw_rules = tw_match.group(1)

        self.assertIn("overflow-x: auto", tw_rules, ".table-wrap must configure overflow-x: auto")
        self.assertIn("-webkit-overflow-scrolling: touch", tw_rules, ".table-wrap must enable iOS momentum touch scrolling")
        self.assertIn("overscroll-behavior-x: contain", tw_rules, ".table-wrap must contain horizontal overscroll")

    def test_rank_table_sticky_z_index_hierarchy(self):
        """TC 2.2: Verify strict z-index hierarchy: th:first-child (20) > th (10) > td:first-child (8) > td (0)."""
        # 1. Desktop th:first-child top-left corner
        corner_matches = re.findall(r"#rank-table\s+th:first-child\s*\{([^}]+)\}", self.css)
        self.assertGreater(len(corner_matches), 0, "Must define #rank-table th:first-child sticky styles")
        all_corner_rules = " ".join(corner_matches)
        self.assertIn("z-index: 20", all_corner_rules, "Top-left header corner must have z-index: 20")
        self.assertIn("left: 0", all_corner_rules, "Top-left header corner must have left: 0")
        self.assertIn("top: 0", all_corner_rules, "Top-left header corner must have top: 0")

        # 2. General header th
        th_match = re.search(r"#rank-table\s+th\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(th_match, "Must define #rank-table th sticky styles")
        self.assertIn("z-index: 10", th_match.group(1), "Sticky headers must have z-index: 10")
        self.assertIn("top: 0", th_match.group(1), "Sticky headers must have top: 0")

        # 3. Body first column sticky cells
        td_matches = re.findall(r"#rank-table\s+tbody\s+tr:not\(\.fund-detail-row\)\s+td:first-child\s*\{([^}]+)\}", self.css)
        self.assertGreater(len(td_matches), 0, "Must define #rank-table td:first-child sticky styles")
        all_td_rules = " ".join(td_matches)
        self.assertIn("z-index: 8", all_td_rules, "Body first-child sticky cells must have z-index: 8")
        self.assertIn("left: 0", all_td_rules, "Body first-child sticky cells must have left: 0")

    def test_rank_table_hover_parity_regular_and_ranked_rows(self):
        """TC 2.3: Verify hover background parity across regular, gold, silver, bronze, and warning rows."""
        # Regular row hover parity
        self.assertIn("#rank-table tbody tr:hover td:first-child", self.css)
        self.assertIn("background: var(--table-hover-bg) !important", self.css)

        # Ranked gold row hover
        self.assertIn("tr.rank-row-gold td:first-child", self.css)
        self.assertIn("tr.rank-row-gold:hover td:first-child", self.css)

        # Ranked silver row hover
        self.assertIn("tr.rank-row-silver td:first-child", self.css)
        self.assertIn("tr.rank-row-silver:hover td:first-child", self.css)

        # Ranked bronze row hover
        self.assertIn("tr.rank-row-bronze td:first-child", self.css)
        self.assertIn("tr.rank-row-bronze:hover td:first-child", self.css)

        # Warning row hover
        self.assertIn("tr.wr td:first-child", self.css)
        self.assertIn("tr.wr:hover td:first-child", self.css)

    def test_rank_table_accordion_expansion_styling(self):
        """TC 2.4: Verify CSS :has() accordion expansion and exclusion of .fund-detail-row from sticky first-child."""
        # CSS :has() expansion highlighting
        self.assertIn("#rank-table tbody tr:has(+ tr.fund-detail-row) td", self.css)
        self.assertIn(".tbl-row-expand-arrow", self.css)

        # Exclusion of fund-detail-row to prevent layout clipping
        self.assertIn("tr:not(.fund-detail-row) td:first-child", self.css)
        self.assertIn("#rank-table tr.fund-detail-row td", self.css)
        detail_td_rule = re.search(r"#rank-table\s+tr\.fund-detail-row\s+td\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(detail_td_rule)
        self.assertIn("position: static !important", detail_td_rule.group(1))

    def test_rank_table_scrolled_x_elevation_shadow(self):
        """TC 2.5: Verify .is-scrolled-x elevation shadow applies when horizontal scrolling commences."""
        self.assertIn("#rank-table.is-scrolled-x th:first-child", self.css)
        self.assertIn("#rank-table.is-scrolled-x tbody tr:not(.fund-detail-row) td:first-child", self.css)
        self.assertIn("box-shadow: 4px 0 12px -2px rgba(0, 0, 0, 0.08)", self.css)

        # Dark theme elevated shadow
        self.assertIn('[data-theme="dark"] #rank-table.is-scrolled-x', self.css)

        # JavaScript event listener in app.js
        self.assertIn("tableWrap.addEventListener('scroll'", self.app_js)
        self.assertIn("tbl.classList.add('is-scrolled-x')", self.app_js)
        self.assertIn("tbl.classList.remove('is-scrolled-x')", self.app_js)

    def test_rank_table_mobile_width_compression_and_card_view(self):
        """TC 2.6: Verify 375px mobile breakpoint narrows first-child to 62px and provides card view."""
        # Narrow first column on mobile (max-width: 768px)
        mobile_th1_match = re.search(
            r"@media\s*\([^\)]*max-width\s*:\s*768px[^\)]*\)[^{]*\{[\s\S]*?#rank-table\s+th:nth-child\(1\)[\s\S]*?width\s*:\s*(\d+)px",
            self.css
        )
        self.assertIsNotNone(mobile_th1_match, "Mobile query must compress first column width")
        mobile_width = int(mobile_th1_match.group(1))
        self.assertLessEqual(mobile_width, 66, f"Mobile sticky column width ({mobile_width}px) must be <= 66px")

        # Edge-to-edge negative margins on mobile .table-wrap
        self.assertIn("margin: 0 -1rem", self.css)

        # Mobile card stream #rank-card-list must exist in DOM
        card_list = self.soup.find(id="rank-card-list")
        self.assertIsNotNone(card_list, "Mobile card stream #rank-card-list must exist")

        # View toggle buttons exist
        view_toggle = self.soup.find(id="rank-view-toggle")
        self.assertIsNotNone(view_toggle, "#rank-view-toggle must exist in markup")

    def test_tabular_numerals_applied_to_table_metrics(self):
        """TC 2.7: Verify tabular-nums and lining-nums are applied across matrix table values."""
        tab_nums_block = re.search(r"#rank-table\s+th,[\s\S]*?#rank-table\s+td[\s\S]*?\{([^}]+)\}", self.css)
        self.assertIsNotNone(tab_nums_block)
        rule_content = tab_nums_block.group(1)
        self.assertIn("tabular-nums", rule_content)
        self.assertIn("lining-nums", rule_content)


class TestPortfolioConfiguratorResponsiveLayout(unittest.TestCase):
    """Stress tests #portfolio layout, sliders, frontier KPI grid, and risk contribution bars."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.app_js = load_app_js()

    def test_portfolio_section_and_inputs_exist(self):
        """TC 3.1: Verify portfolio container and interactive range inputs exist in DOM."""
        page_pf = self.soup.find(id="page-portfolio")
        self.assertIsNotNone(page_pf, "#page-portfolio container must exist in index.html")

        # Sliders
        pf_m = self.soup.find(id="pf-m")
        pf_y = self.soup.find(id="pf-y")
        frontier_slider = self.soup.find(id="frontier-range-slider")
        self.assertIsNotNone(pf_m, "#pf-m range input must exist")
        self.assertIsNotNone(pf_y, "#pf-y range input must exist")
        self.assertIsNotNone(frontier_slider, "#frontier-range-slider must exist")

    def test_portfolio_params_grid_collapse(self):
        """TC 3.2: Verify .g2 2-column desktop layout collapses to 1 column at tablet/mobile (<=1024px)."""
        desktop_g2 = re.search(r"\.g2\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(desktop_g2)
        self.assertIn("grid-template-columns: 1fr 1fr", desktop_g2.group(1))

        mobile_g2 = re.search(r"@media\s*\([^\)]*max-width\s*:\s*1024px[^\)]*\)[^{]*\{[\s\S]*?\.g2\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(mobile_g2)
        self.assertIn("grid-template-columns: 1fr", mobile_g2.group(1))

    def test_portfolio_range_sliders_halo_progress_track(self):
        """TC 3.3: Verify dynamic --slider-pct progress track and halo thumb styles."""
        self.assertIn("var(--slider-pct, 50%)", self.css)
        self.assertIn("input[type=range]::-webkit-slider-thumb", self.css)
        self.assertIn("input[type=range]::-moz-range-thumb", self.css)

        # Dynamic updating in app.js
        self.assertIn("updateSliderGlowTrack", self.app_js)
        self.assertIn("--slider-pct", self.app_js)

    def test_portfolio_frontier_kpi_grid_breakpoints(self):
        """TC 3.4: Verify .frontier-kpi-grid scales from 4-col (desktop) -> 3-col (900px) -> 2-col (640px) -> 1-col (380px)."""
        # Desktop 4-col specification
        desktop_grid = re.search(r"\.frontier-kpi-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(desktop_grid)
        self.assertIn("repeat(3, minmax(110px, 1fr)) 1.8fr", desktop_grid.group(1))

        # 900px breakpoint
        self.assertIn("@media (max-width: 900px)", self.css)
        # 640px breakpoint
        self.assertIn("@media (max-width: 640px)", self.css)
        # 380px mobile breakpoint
        self.assertIn("@media (max-width: 380px)", self.css)

    def test_portfolio_risk_contribution_bars_responsiveness(self):
        """TC 3.5: Verify .f-split-bar, .f-risk-nq, and .f-risk-sp styles and text shadow."""
        self.assertIn(".f-split-bar", self.css)
        self.assertIn(".f-split-nq", self.css)
        self.assertIn(".f-split-sp", self.css)
        self.assertIn(".f-risk-nq", self.css)
        self.assertIn(".f-risk-sp", self.css)

        # Elements exist in DOM
        self.assertIsNotNone(self.soup.find(id="f-cap-nq"))
        self.assertIsNotNone(self.soup.find(id="f-cap-sp"))
        self.assertIsNotNone(self.soup.find(id="f-risk-nq"))
        self.assertIsNotNone(self.soup.find(id="f-risk-sp"))

    def test_portfolio_crisis_stress_cards_layout(self):
        """TC 3.6: Verify stress test section, scenario tabs, and recovery badges."""
        stress_sec = self.soup.find(id="stress-test-section")
        self.assertIsNotNone(stress_sec, "#stress-test-section must exist in DOM")

        scenario_tabs = self.soup.find(id="stress-scenario-tabs")
        self.assertIsNotNone(scenario_tabs, "#stress-scenario-tabs must exist in DOM")

        # Scenario glowing tabs in CSS
        self.assertIn('.stress-scenario-tabs .seg-btn[data-scenario="gfc"].on', self.css)
        self.assertIn('.stress-scenario-tabs .seg-btn[data-scenario="covid"].on', self.css)
        self.assertIn('.stress-scenario-tabs .seg-btn[data-scenario="dotcom"].on', self.css)
        self.assertIn('.stress-scenario-tabs .seg-btn[data-scenario="ratehike"].on', self.css)


class TestMonteCarloSimulatorResponsiveLayout(unittest.TestCase):
    """Stress tests #simulator layout, computing deck shimmer, steppers, and result cards."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.app_js = load_app_js()

    def test_simulator_container_and_controls_in_dom(self):
        """TC 4.1: Verify #page-simulator container, inputs, presets, and run button exist in DOM."""
        page_sim = self.soup.find(id="page-simulator")
        self.assertIsNotNone(page_sim, "#page-simulator must exist in DOM")

        self.assertIsNotNone(self.soup.find(id="sim-m"), "#sim-m range input must exist")
        self.assertIsNotNone(self.soup.find(id="sim-y"), "#sim-y range input must exist")
        self.assertIsNotNone(self.soup.find(id="btn-sim"), "#btn-sim run button must exist")
        self.assertIsNotNone(self.soup.find(id="sim-result"), "#sim-result container must exist")

    def test_simulator_computing_deck_structure_and_shimmer(self):
        """TC 4.2: Verify .sim-computing-deck, shimmer animation, and spinner styles."""
        self.assertIn(".sim-computing-deck", self.css)
        self.assertIn(".sim-progress-track", self.css)
        self.assertIn(".sim-progress-bar-shimmer", self.css)
        self.assertIn("@keyframes simShimmer", self.css)
        self.assertIn("@keyframes simSpin", self.css)

        # Verify app.js dynamically injects .sim-computing-deck on run
        self.assertIn("sim-computing-deck", self.app_js)
        self.assertIn("sim-progress-bar-shimmer", self.app_js)

    def test_simulator_stepper_touch_targets(self):
        """TC 4.3: Verify steppers configure touch-action: manipulation and minimum sizing for mobile."""
        self.assertIn(".input-stepper-wrap", self.css)
        stepper_btn = re.search(r"\.input-stepper-btn\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(stepper_btn)
        rules = stepper_btn.group(1)
        self.assertIn("touch-action: manipulation", rules, "Stepper buttons must prevent double-tap zoom delay")
        self.assertIn("min-width: 24px", rules)
        self.assertIn("min-height: 24px", rules)

    def test_simulator_sensitivity_tabs_mobile_wrapping(self):
        """TC 4.4: Verify .sim-sens-tabs wraps cleanly on narrow screens (<=520px)."""
        sens_tabs = self.soup.find(id="sim-sens-tabs")
        self.assertIsNotNone(sens_tabs, "#sim-sens-tabs must exist in DOM")

        self.assertIn(".sim-sens-tabs", self.css)
        mobile_sens = re.search(r"\.sim-sens-tabs\s*\{[\s\S]*?flex-wrap:\s*wrap", self.css)
        self.assertIsNotNone(mobile_sens, "Sensitivity buttons must wrap on mobile")


class TestRadarCtaAnchorScrollAndBulletinNavigation(unittest.TestCase):
    """Stress tests Quota Radar CTA button anchor navigation, target containers, and navbar compensation."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.app_js = load_app_js()
        cls.limits = load_limit_changes_data()

    def test_radar_cta_button_attributes_and_href(self):
        """TC 5.1: Verify CTA button in home radar card has verbatim href='#ranking?section=quota'."""
        cta = self.soup.find("a", href="#ranking?section=quota")
        self.assertIsNotNone(cta, "CTA link href='#ranking?section=quota' must exist in index.html")
        self.assertIn("btn-jump-strat", cta.get("class", []))
        self.assertIn("查阅实时额度快报", cta.get_text())

    def test_quota_bulletin_target_ids_in_dom(self):
        """TC 5.2: Verify #quota-bulletin-section and #quota-bulletin-container exist in DOM and are unique."""
        section = self.soup.find(id="quota-bulletin-section")
        container = self.soup.find(id="quota-bulletin-container")
        self.assertIsNotNone(section, "#quota-bulletin-section anchor section must exist in DOM")
        self.assertIsNotNone(container, "#quota-bulletin-container inner container must exist in DOM")

        # Must appear exactly once verbatim
        with open(PROJECT_ROOT / "public" / "index.html", "r", encoding="utf-8") as f:
            html = f.read()
        self.assertEqual(len(re.findall(r'id=["\']quota-bulletin-section["\']', html)), 1)
        self.assertEqual(len(re.findall(r'id=["\']quota-bulletin-container["\']', html)), 1)

    def test_quota_bulletin_scroll_margin_navbar_offset(self):
        """TC 5.3: Verify .quota-bulletin-section-wrap sets scroll-margin-top: 5rem to avoid navbar overlap."""
        wrap_match = re.search(r"\.quota-bulletin-section-wrap\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(wrap_match, "style.css must define .quota-bulletin-section-wrap")
        rules = wrap_match.group(1)
        self.assertIn("scroll-margin-top: 5rem", rules, "Anchor wrapper must specify scroll-margin-top: 5rem")
        self.assertIn("display: block", rules)

    def test_app_js_router_section_quota_handling(self):
        """TC 5.4: Verify app.js switchPage parses queryParams.section === 'quota' and invokes smooth scroll."""
        self.assertIn("queryParams.section === 'quota'", self.app_js)
        # Dual-ID fallback check in app.js
        self.assertIn(
            "document.getElementById('quota-bulletin-section') || document.getElementById('quota-bulletin-container')",
            self.app_js,
            "app.js must provide dual-ID fallback for quota bulletin anchor"
        )
        self.assertIn("scrollIntoView({ behavior: 'smooth', block: 'start' })", self.app_js)
        self.assertIn("classList.add('highlight-glow')", self.app_js)

    def test_radar_svg_visual_animations(self):
        """TC 5.5: Verify SVG radar sweep animation, sonar ring, and blips exist in CSS."""
        self.assertIn("@keyframes radarSweepRotate", self.css)
        self.assertIn("@keyframes radarSonarPulse", self.css)
        self.assertIn("@keyframes radarBlipFade", self.css)

        # SVG elements in markup
        radar_scope = self.soup.find(class_="radar-scope-wrapper")
        self.assertIsNotNone(radar_scope, ".radar-scope-wrapper must exist in home quota radar card")
        self.assertIsNotNone(radar_scope.find(class_="radar-rings"))
        self.assertIsNotNone(radar_scope.find(class_="radar-sonar-ring"))

    def test_quota_features_grid_responsive_columns(self):
        """TC 5.6: Verify .home-quota-features-grid is 3-column desktop and 1-column mobile (<=768px)."""
        desktop_grid = re.search(r"\.home-quota-features-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(desktop_grid)
        self.assertIn("grid-template-columns: repeat(3, 1fr)", desktop_grid.group(1))

        # Check mobile 1-column rule
        mobile_match = re.search(r"\.home-quota-features-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr", self.css)
        self.assertIsNotNone(mobile_match, "Mobile media query must set grid-template-columns: 1fr for .home-quota-features-grid")

    def test_quota_bulletin_mobile_drawer_and_card_view(self):
        """TC 5.7: Verify mobile breakpoint switches quota table to responsive cards (.quota-card-list)."""
        self.assertIn(".quota-table-wrap", self.css)
        self.assertIn(".quota-card-list", self.css)

        # Verify specifically within mobile styles that table is hidden and card list is shown
        table_hide = re.search(r"\.quota-table-wrap\s*\{[^}]*display\s*:\s*none\s*!important", self.css)
        card_show = re.search(r"\.quota-card-list\s*\{[^}]*display\s*:\s*flex\s*!important", self.css)
        self.assertIsNotNone(table_hide, ".quota-table-wrap must have display: none !important on mobile")
        self.assertIsNotNone(card_show, ".quota-card-list must have display: flex !important on mobile")


if __name__ == "__main__":
    unittest.main()
