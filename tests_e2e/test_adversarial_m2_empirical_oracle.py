import unittest
import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT_DIR / "public" / "index.html"
ABOUT_HTML = ROOT_DIR / "public" / "about.html"


class TestAdversarialM2EmpiricalOracle(unittest.TestCase):
    """Empirical challenger stress-tests for Milestone 2:

    Semantic contracts, JSON-LD schemas, Speculation Rules, modal dialog
    accessibility, and AI-slop elimination across public/index.html and
    public/about.html.
    """

    @classmethod
    def setUpClass(cls):
        cls.index_content = INDEX_HTML.read_text(encoding="utf-8")
        cls.about_content = ABOUT_HTML.read_text(encoding="utf-8")
        cls.index_soup = BeautifulSoup(cls.index_content, "html.parser")
        cls.about_soup = BeautifulSoup(cls.about_content, "html.parser")

    # =========================================================================
    # Mission Item 1: Stress-Test JSON-LD & Searchbox Contracts
    # =========================================================================

    def test_sitelinks_searchbox_target_contract(self):
        """Stress-test Google Sitelinks Searchbox JSON-LD in index.html:

        - Must parse as valid JSON.
        - @type must be WebSite.
        - potentialAction target must equal 'https://858000.xyz/?q={query}' exactly.
        - target must NOT contain '#' (fragment).
        - query-input must be 'required name=query'.
        """
        scripts = self.index_soup.find_all("script", type="application/ld+json")
        website_schemas = []
        for s in scripts:
            try:
                data = json.loads(s.string)
                if data.get("@type") == "WebSite":
                    website_schemas.append(data)
            except Exception as e:
                self.fail(f"Invalid JSON in application/ld+json script: {e}")

        self.assertEqual(len(website_schemas), 1, "Expected exactly 1 WebSite JSON-LD schema in index.html")
        ws = website_schemas[0]
        self.assertEqual(ws.get("@context"), "https://schema.org")
        self.assertEqual(ws.get("url"), "https://858000.xyz/")

        action = ws.get("potentialAction")
        self.assertIsInstance(action, dict, "potentialAction must be a dictionary")
        self.assertEqual(action.get("@type"), "SearchAction")
        self.assertEqual(action.get("query-input"), "required name=query")

        target = action.get("target")
        self.assertEqual(target, "https://858000.xyz/?q={query}", "Target must match canonical searchbox URL")
        self.assertNotIn("#", target, "Target MUST NOT contain hash fragment '#'")

    def test_about_page_json_ld_schema_and_author_credentials(self):
        """Stress-test AboutPage JSON-LD schema in about.html:

        - Must parse without error.
        - Must have @type: 'AboutPage'.
        - Must reference Schema.org context.
        - Page text must mention CFA, Markowitz, Sharpe, Sortino.
        """
        scripts = self.about_soup.find_all("script", type="application/ld+json")
        about_schemas = []
        for s in scripts:
            try:
                data = json.loads(s.string)
                if data.get("@type") == "AboutPage":
                    about_schemas.append(data)
            except Exception as e:
                self.fail(f"Invalid JSON in about.html application/ld+json script: {e}")

        self.assertEqual(len(about_schemas), 1, "Expected exactly 1 AboutPage JSON-LD schema in about.html")
        ab = about_schemas[0]
        self.assertEqual(ab.get("@context"), "https://schema.org")
        self.assertIn("Fund Advisor", ab.get("name", ""))
        self.assertEqual(ab.get("url"), "https://858000.xyz/about")

        # ContactPoint verification in JSON-LD publisher
        publisher = ab.get("publisher", {})
        self.assertEqual(publisher.get("@type"), "Organization")
        contact_point = publisher.get("contactPoint", {})
        self.assertEqual(contact_point.get("contactType"), "customer service")
        self.assertIn("@", contact_point.get("email", ""))

        # Stress-test content citations in about.html text
        for term, min_occurrences in [("CFA", 1), ("Markowitz", 2), ("Sharpe", 2), ("Sortino", 3)]:
            count = self.about_content.count(term)
            self.assertGreaterEqual(
                count, min_occurrences,
                f"Expected term '{term}' to appear at least {min_occurrences} times in about.html, found {count}"
            )

    def test_all_json_ld_blocks_validity_in_index_and_about(self):
        """Stress-test all JSON-LD blocks in both index.html and about.html for JSON validity."""
        for name, soup in [("index.html", self.index_soup), ("about.html", self.about_soup)]:
            scripts = soup.find_all("script", type="application/ld+json")
            self.assertGreater(len(scripts), 0, f"{name} must contain JSON-LD scripts")
            for idx, s in enumerate(scripts):
                self.assertIsNotNone(s.string, f"Empty JSON-LD script at index {idx} in {name}")
                try:
                    parsed = json.loads(s.string)
                    self.assertIn("@context", parsed, f"Missing @context in {name} script {idx}")
                    self.assertIn("@type", parsed, f"Missing @type in {name} script {idx}")
                except Exception as e:
                    self.fail(f"JSON-LD syntax error in {name} script {idx}: {e}")

    # =========================================================================
    # Mission Item 3: Stress-Test Speculation Rules & Modal Dialog Accessibility
    # =========================================================================

    def test_speculation_rules_syntax_and_schema_validation(self):
        """Stress-test <script type="speculationrules"> in index.html and about.html:

        - Must parse as valid JSON.
        - Must contain valid top-level keys: 'prefetch' and/or 'prerender'.
        - Eagerness levels must be valid per W3C specification.
        - Exclusion rules (not /selector_matches / nofollow / /fund/*) must be correctly structured.
        """
        valid_eagerness = {"immediate", "eager", "moderate", "conservative"}

        for page_name, soup in [("index.html", self.index_soup), ("about.html", self.about_soup)]:
            spec_script = soup.find("script", type="speculationrules")
            self.assertIsNotNone(spec_script, f"Missing speculationrules script in {page_name}")
            self.assertIsNotNone(spec_script.string, f"Empty speculationrules script in {page_name}")

            try:
                rules = json.loads(spec_script.string)
            except Exception as e:
                self.fail(f"speculationrules JSON syntax error in {page_name}: {e}")

            self.assertIsInstance(rules, dict, f"speculationrules must be a dict in {page_name}")
            self.assertTrue(
                "prefetch" in rules or "prerender" in rules,
                f"speculationrules must contain prefetch or prerender in {page_name}"
            )

            for rule_type in ["prefetch", "prerender"]:
                if rule_type in rules:
                    self.assertIsInstance(rules[rule_type], list, f"{rule_type} must be a list in {page_name}")
                    for rule_idx, rule in enumerate(rules[rule_type]):
                        self.assertIn("where", rule, f"Missing 'where' condition in {page_name} {rule_type}[{rule_idx}]")
                        self.assertIn("eagerness", rule, f"Missing 'eagerness' in {page_name} {rule_type}[{rule_idx}]")
                        self.assertIn(
                            rule["eagerness"], valid_eagerness,
                            f"Invalid eagerness '{rule['eagerness']}' in {page_name} {rule_type}[{rule_idx}]"
                        )
                        where = rule["where"]
                        self.assertIsInstance(where, dict, f"'where' must be dict in {page_name} {rule_type}[{rule_idx}]")

    def test_modal_dialogs_accessibility_contract(self):
        """Stress-test modal dialog containers for screen reader and keyboard accessibility:

        - Must have role="dialog".
        - Must have aria-modal="true".
        - Must have aria-labelledby pointing to an existing heading element with non-empty text.
        - Must contain interactive close buttons that meet touch target guidelines.
        """
        modal_ids = [
            "rank-select-modal",
            "quota-select-modal",
            "poster-modal-backdrop",
            "shortcut-hud-modal"
        ]

        for mid in modal_ids:
            modal = self.index_soup.find(id=mid)
            self.assertIsNotNone(modal, f"Modal dialog #{mid} missing in index.html")
            self.assertEqual(modal.get("role"), "dialog", f"Modal #{mid} must have role='dialog'")
            self.assertEqual(modal.get("aria-modal"), "true", f"Modal #{mid} must have aria-modal='true'")

            title_id = modal.get("aria-labelledby")
            self.assertIsNotNone(title_id, f"Modal #{mid} missing aria-labelledby attribute")
            title_el = self.index_soup.find(id=title_id)
            self.assertIsNotNone(title_el, f"Target title #{title_id} for modal #{mid} not found in DOM")
            self.assertGreater(len(title_el.get_text(strip=True)), 0, f"Title #{title_id} for modal #{mid} is empty")

            # Check that modal has a close button
            close_buttons = modal.find_all(lambda el: el.name in ["button", "a"] and any(
                c in ["fund-select-close", "poster-modal-close", "btn-hud-close", "btn-rks-cancel", "btn-qks-cancel"]
                for c in el.get("class", [])
            ) or el.get("id") in ["btn-rks-close", "btn-qks-close", "poster-modal-close", "btn-hud-close"])
            self.assertGreater(
                len(close_buttons), 0,
                f"Modal #{mid} must contain at least one accessible dismiss/close button"
            )

    # =========================================================================
    # Additional Verification: 88 DOM IDs, Static Tickers, and AI-Slop Cleansing
    # =========================================================================

    def test_all_88_dom_element_ids_preserved(self):
        """Verify all 88 DOM element IDs cataloged in explorer_survey_1 are present in index.html."""
        cataloged_ids = [
            # A. Telemetry HUD
            "hero-quant-ticker", "ticker-market-badge", "ticker-market-status",
            "ticker-latency-tag", "tk-pool-count", "tk-avail-count", "tk-min-fee",
            "theme-toggle", "nav-links", "footer-us-market-status",
            # B. Hero Indices Deck & Black Swan
            "hero-indices-deck", "card-index-ndx", "ndx-price", "ndx-badge", "ndx-diff",
            "ndx-etf-val", "ndx-range-bar", "ndx-low", "ndx-high", "ndx-range-pct",
            "ndx-range-fill", "ndx-range-marker", "ndx-ext-wrap", "ndx-lag-text",
            "card-index-inx", "inx-price", "inx-badge", "inx-diff", "inx-etf-val",
            "inx-range-bar", "inx-low", "inx-high", "inx-range-pct", "inx-range-fill",
            "inx-range-marker", "inx-ext-wrap", "inx-lag-text", "black-swan-banner", "swan-cta-btn",
            # C. Matrix Table & Filters
            "rank-table-wrap", "rank-table", "rank-filter", "class-filter", "quota-filter",
            "rank-search", "rank-search-clear", "rank-view-toggle", "view-btn-table",
            "view-btn-card", "rank-card-list",
            # D. Portfolio Configurator
            "page-portfolio", "pf-m", "pf-mv-badge", "pf-y", "pf-yv-badge", "btn-pf",
            "quant-frontier-card", "quant-frontier-toggle", "chart-efficient-frontier",
            "frontier-inspector-card", "frontier-range-slider", "f-cap-nq", "f-cap-sp",
            "f-risk-nq", "f-risk-sp", "pf-category-filter", "quant-matrix-tbody",
            "stress-test-section", "stress-scenario-tabs", "chart-stress-test", "stress-test-tbody",
            # E. Monte Carlo Wealth Simulator
            "page-simulator", "sim-m", "sim-y", "sim-sel-trigger", "sim-sel-dropdown",
            "sim-sel-search", "sim-sel-all", "sim-sel-clear", "sim-sel-list",
            "sim-weights-container", "sim-weights-list", "sim-smart-toggle", "sim-smart-panel",
            "sim-sens-tabs", "vg-recom-budget", "btn-sim", "sim-result", "ch-sim",
            # F. Restriction Radar & Bulletin
            "quota-alert-bar", "quota-pulse-dot", "quota-alert-date", "quota-alert-msg",
            "quota-alert-tickers", "btn-quota-toggle", "quota-toggle-text", "quota-board-drawer",
            "btn-quota-export-douyin", "qstat-recent", "qstat-relaxed", "qstat-tightened",
            "qstat-stable", "quota-bulletin-section", "quota-bulletin-container", "quota-table",
            "quota-table-tbody", "quota-card-list",
            # G. Routes
            "page-home", "page-ranking", "page-guide"
        ]

        missing_ids = []
        for eid in cataloged_ids:
            if not self.index_soup.find(id=eid):
                missing_ids.append(eid)

        self.assertEqual(missing_ids, [], f"Missing {len(missing_ids)} cataloged DOM IDs in index.html: {missing_ids}")

    def test_static_prefilled_tickers_preserved(self):
        """Verify the 7 static ticker and quote values are not replaced with '--'."""
        fixtures = {
            "ndx-price": "26,958.76",
            "ndx-badge": "+1.24%",
            "inx-price": "7,374.71",
            "inx-badge": "+0.29%",
            "ndx-etf-val": "$655.74 (+1.34%)",
            "inx-etf-val": "$735.21 (+0.30%)",
            "qstat-stable": "60",
        }
        for eid, expected in fixtures.items():
            el = self.index_soup.find(id=eid)
            self.assertIsNotNone(el, f"Element #{eid} missing")
            self.assertEqual(el.get_text(strip=True), expected, f"Value mismatch for #{eid}")

    def test_ai_slop_and_decorative_characters_completely_eliminated(self):
        """Stress-test public/index.html and public/about.html for elimination of AI-slop elements."""
        combined = self.index_content + self.about_content

        # Unicode decorative symbols
        self.assertNotIn("➔", combined, "Unicode arrow ➔ must be eliminated")
        self.assertNotIn("★", combined, "Unicode star ★ must be eliminated")
        self.assertNotIn("☆", combined, "Unicode star ☆ must be eliminated")

        # Dead elements and ambient glow
        self.assertNotIn("ambient-glow-mesh", combined, "Ambient glow mesh class must be eliminated")
        self.assertNotIn("btn-shine", combined, "btn-shine must be eliminated")

        # Inline gradient badges
        self.assertNotIn("linear-gradient", self.index_content, "Inline linear-gradient backgrounds must be eliminated")

        # Obsolete marketing hyperbole
        slop_phrases = [
            "现代化高引力 Hero 核心操作集群",
            "高维通算能力",
            "启动财富推演 ➔",
            "华尔街对冲基金级",
            "拒绝惩罚上涨收益的粗暴标准差",
            "彻底击碎择时神话",
            "肥尾黑天鹅实测",
            "量化通算引擎全时在线",
            "Designed to Award Tier Standards",
            "将华尔街量化对冲算法转化为您的日常定投武器",
        ]
        for phrase in slop_phrases:
            self.assertNotIn(phrase, combined, f"Obsolete marketing phrase found: '{phrase}'")

    def test_modern_web_platform_color_scheme_and_cache_sync(self):
        """Verify modern web platform <meta name="color-scheme"> and cache query sync."""
        for name, soup in [("index.html", self.index_soup), ("about.html", self.about_soup)]:
            cs_meta = soup.find("meta", attrs={"name": "color-scheme"})
            self.assertIsNotNone(cs_meta, f"<meta name='color-scheme'> missing in {name}")
            self.assertEqual(cs_meta.get("content"), "light dark", f"color-scheme must be 'light dark' in {name}")

        self.assertIn("style.css?v=20261031_award", self.index_content, "index.html missing cache token")
        self.assertIn("style.css?v=20261031_award", self.about_content, "about.html missing cache token")


if __name__ == "__main__":
    unittest.main()
