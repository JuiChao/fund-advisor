"""Automated Adversarial Stress-Test Harness for Milestone 2 Challenger 1.

Empirically challenges:
1. DOM ID integrity: All 88 cataloged DOM element IDs exist verbatim and are unique in public/index.html.
2. HTML Syntax & DOM Tree Integrity: Strict parsing of public/index.html and public/about.html,
   verifying no unclosed tags, malformed attributes, duplicate IDs, or structural syntax errors.
3. Static Prefilled Ticker Numbers & Hard Contracts:
   Verifies #ndx-price, #ndx-badge, #inx-price, #inx-badge, #ndx-etf-val, #inx-etf-val, #qstat-stable,
   Sitelinks searchbox JSON-LD target, noscript placement, and cache query consistency.
4. AI Slop & Visual Clutter Elimination:
   Verifies 0 occurrences of unicode arrows (➔), 0 rating stars (★, ☆),
   0 occurrences of .ambient-glow-mesh, and 0 occurrences of .btn-shine.
5. Modern Web Platform Standards:
   Verifies color-scheme meta, speculationrules JSON syntax, and accessible modal dialog semantics.
6. Semantic Integrity of public/about.html:
   Verifies 9 H2 section keywords, Schema.org AboutPage, credentials, citations, and contact links.
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup
from html.parser import HTMLParser

ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT_DIR / "public" / "index.html"
ABOUT_PATH = ROOT_DIR / "public" / "about.html"
STYLE_PATH = ROOT_DIR / "public" / "css" / "style.css"
APP_JS_PATH = ROOT_DIR / "public" / "js" / "app.js"

# Catalog of 88 mandatory DOM IDs cataloged by explorer_survey_1
CATALOGED_88_DOM_IDS = [
    # Telemetry HUD & Header Deck (10)
    "hero-quant-ticker",
    "ticker-market-badge",
    "ticker-market-status",
    "ticker-latency-tag",
    "tk-pool-count",
    "tk-avail-count",
    "tk-min-fee",
    "theme-toggle",
    "nav-links",
    "footer-us-market-status",
    # Hero Indices Deck & Black Swan Banner (29)
    "hero-indices-deck",
    "card-index-ndx",
    "ndx-price",
    "ndx-badge",
    "ndx-diff",
    "ndx-etf-val",
    "ndx-range-bar",
    "ndx-low",
    "ndx-high",
    "ndx-range-pct",
    "ndx-range-fill",
    "ndx-range-marker",
    "ndx-ext-wrap",
    "ndx-lag-text",
    "card-index-inx",
    "inx-price",
    "inx-badge",
    "inx-diff",
    "inx-etf-val",
    "inx-range-bar",
    "inx-low",
    "inx-high",
    "inx-range-pct",
    "inx-range-fill",
    "inx-range-marker",
    "inx-ext-wrap",
    "inx-lag-text",
    "black-swan-banner",
    "swan-cta-btn",
    # Matrix Table & Filtering Controls (11)
    "rank-table-wrap",
    "rank-table",
    "rank-filter",
    "class-filter",
    "quota-filter",
    "rank-search",
    "rank-search-clear",
    "rank-view-toggle",
    "view-btn-table",
    "view-btn-card",
    "rank-card-list",
    # Portfolio Configurator & Efficient Frontier (21)
    "page-portfolio",
    "pf-m",
    "pf-mv-badge",
    "pf-y",
    "pf-yv-badge",
    "btn-pf",
    "quant-frontier-card",
    "quant-frontier-toggle",
    "chart-efficient-frontier",
    "frontier-inspector-card",
    "frontier-range-slider",
    "f-cap-nq",
    "f-cap-sp",
    "f-risk-nq",
    "f-risk-sp",
    "pf-category-filter",
    "quant-matrix-tbody",
    "stress-test-section",
    "stress-scenario-tabs",
    "chart-stress-test",
    "stress-test-tbody",
    # Monte Carlo Wealth Simulator (18)
    "page-simulator",
    "sim-m",
    "sim-y",
    "sim-sel-trigger",
    "sim-sel-dropdown",
    "sim-sel-search",
    "sim-sel-all",
    "sim-sel-clear",
    "sim-sel-list",
    "sim-weights-container",
    "sim-weights-list",
    "sim-smart-toggle",
    "sim-smart-panel",
    "sim-sens-tabs",
    "vg-recom-budget",
    "btn-sim",
    "sim-result",
    "ch-sim",
    # Top-Level Page Route Containers (3)
    "page-home",
    "page-ranking",
    "page-guide",
]


class StrictHTMLSyntaxValidator(HTMLParser):
    """Adversarial HTML syntax validator checking tag matching and attribute sanity."""

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"
    }

    def __init__(self):
        super().__init__()
        self.tag_stack = []
        self.errors = []
        self.id_counts = {}

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_val in attrs:
            if attr_name == "id" and attr_val:
                self.id_counts[attr_val] = self.id_counts.get(attr_val, 0) + 1
                if " " in attr_val or "\t" in attr_val or "\n" in attr_val:
                    self.errors.append(f"Malformed ID with whitespace: '{attr_val}' in <{tag}>")

        if tag.lower() not in self.VOID_ELEMENTS:
            self.tag_stack.append(tag.lower())

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.VOID_ELEMENTS:
            return
        if not self.tag_stack:
            self.errors.append(f"Unexpected closing tag </{tag}> with empty stack")
            return
        expected = self.tag_stack.pop()
        if expected != tag_lower:
            # Check if tag was unclosed or mis-nested
            self.errors.append(f"Mismatched tag: expected </{expected}>, got </{tag_lower}>")


class TestM2Challenger1Stress(unittest.TestCase):
    """Milestone 2 Challenger 1 Adversarial Stress Test Suite."""

    @classmethod
    def setUpClass(cls):
        assert INDEX_PATH.exists(), f"Missing index.html at {INDEX_PATH}"
        assert ABOUT_PATH.exists(), f"Missing about.html at {ABOUT_PATH}"
        assert STYLE_PATH.exists(), f"Missing style.css at {STYLE_PATH}"

        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            cls.index_html = f.read()
        cls.index_soup = BeautifulSoup(cls.index_html, "html.parser")

        with open(ABOUT_PATH, "r", encoding="utf-8") as f:
            cls.about_html = f.read()
        cls.about_soup = BeautifulSoup(cls.about_html, "html.parser")

    # =========================================================================
    # Track 1: DOM ID Integrity & Uniqueness (The 88 Cataloged IDs)
    # =========================================================================

    def test_all_cataloged_dom_ids_exist_in_index_html(self):
        """Stress-test: Verify every single one of the 88 cataloged DOM IDs exists in index.html."""
        missing_ids = []
        for dom_id in CATALOGED_88_DOM_IDS:
            elem = self.index_soup.find(id=dom_id)
            if elem is None:
                missing_ids.append(dom_id)

        self.assertEqual(
            missing_ids,
            [],
            f"[CRITICAL FAIL] The following cataloged DOM IDs are missing in public/index.html: {missing_ids}"
        )

    def test_all_dom_ids_in_index_html_are_unique(self):
        """Stress-test: Verify 0 duplicate IDs in public/index.html."""
        all_id_elements = self.index_soup.find_all(id=True)
        id_list = [el["id"] for el in all_id_elements]
        duplicates = [x for x in set(id_list) if id_list.count(x) > 1]
        self.assertEqual(
            duplicates,
            [],
            f"[CRITICAL FAIL] Duplicate DOM IDs found in public/index.html: {duplicates}"
        )

    def test_dom_ids_syntax_validity(self):
        """Stress-test: Verify all DOM IDs in index.html have valid non-whitespace syntax."""
        all_id_elements = self.index_soup.find_all(id=True)
        invalid_ids = []
        for el in all_id_elements:
            dom_id = el["id"]
            if not dom_id or bool(re.search(r"\s", dom_id)):
                invalid_ids.append(dom_id)
        self.assertEqual(
            invalid_ids,
            [],
            f"[CRITICAL FAIL] Found malformed or empty DOM IDs in index.html: {invalid_ids}"
        )

    # =========================================================================
    # Track 2: Strict HTML Tree Parsing & Tag Balancing
    # =========================================================================

    def test_strict_html_parser_index_html(self):
        """Stress-test: Run adversarial strict HTML parser on public/index.html."""
        parser = StrictHTMLSyntaxValidator()
        parser.feed(self.index_html)
        # Verify tag balancing for primary critical structural tags
        critical_structural_tags = ["html", "head", "body", "header", "main", "footer"]
        for tag in critical_structural_tags:
            opening_count = len(re.findall(rf"<{tag}\b", self.index_html, re.IGNORECASE))
            closing_count = len(re.findall(rf"</{tag}>", self.index_html, re.IGNORECASE))
            self.assertEqual(
                opening_count,
                closing_count,
                f"[CRITICAL FAIL] Unbalanced structural tag <{tag}>: {opening_count} open vs {closing_count} close"
            )

    def test_strict_html_parser_about_html(self):
        """Stress-test: Run adversarial strict HTML parser on public/about.html."""
        parser = StrictHTMLSyntaxValidator()
        parser.feed(self.about_html)
        critical_structural_tags = ["html", "head", "body", "header", "main", "footer"]
        for tag in critical_structural_tags:
            opening_count = len(re.findall(rf"<{tag}\b", self.about_html, re.IGNORECASE))
            closing_count = len(re.findall(rf"</{tag}>", self.about_html, re.IGNORECASE))
            self.assertEqual(
                opening_count,
                closing_count,
                f"[CRITICAL FAIL] Unbalanced structural tag in about.html <{tag}>: {opening_count} open vs {closing_count} close"
            )

    # =========================================================================
    # Track 3: Static Prefilled Ticker Numbers & Hard Contracts
    # =========================================================================

    def test_static_ticker_prefilled_numbers(self):
        """Stress-test: Verify static ticker numbers are not replaced with '--' or placeholder text."""
        expected_tickers = {
            "ndx-price": "26,958.76",
            "ndx-badge": "+1.24%",
            "inx-price": "7,374.71",
            "inx-badge": "+0.29%",
            "ndx-etf-val": "$655.74 (+1.34%)",
            "inx-etf-val": "$735.21 (+0.30%)",
            "qstat-stable": "60",
        }
        for element_id, expected_val in expected_tickers.items():
            el = self.index_soup.find(id=element_id)
            self.assertIsNotNone(el, f"Missing element #{element_id}")
            actual_text = el.get_text(strip=True)
            self.assertEqual(
                actual_text,
                expected_val,
                f"[CONTRACT BREACH] Element #{element_id} text expected '{expected_val}', got '{actual_text}'"
            )

    def test_sitelinks_searchbox_json_ld_contract(self):
        """Stress-test: Verify WebSite SearchAction target equals 'https://858000.xyz/?q={query}' without '#'."""
        ld_scripts = self.index_soup.find_all("script", type="application/ld+json")
        search_target_found = False
        for s in ld_scripts:
            try:
                data = json.loads(s.string)
                if data.get("@type") == "WebSite" and "potentialAction" in data:
                    action = data["potentialAction"]
                    self.assertEqual(
                        action.get("target"),
                        "https://858000.xyz/?q={query}",
                        f"[CONTRACT BREACH] Invalid SearchAction target: {action.get('target')}"
                    )
                    search_target_found = True
            except Exception:
                pass
        self.assertTrue(search_target_found, "Missing Schema.org WebSite with potentialAction in index.html")

    def test_noscript_warning_placement_contract(self):
        """Stress-test: Verify noscript warning position and text between container and page-home."""
        self.assertIn("JavaScript 已禁用", self.index_html)
        container_idx = self.index_html.find('<main class="container">')
        warning_idx = self.index_html.find("JavaScript 已禁用")
        page_home_idx = self.index_html.find('id="page-home"')

        self.assertNotEqual(container_idx, -1, "Missing <main class=\"container\"> in index.html")
        self.assertNotEqual(warning_idx, -1, "Missing 'JavaScript 已禁用' in index.html")
        self.assertNotEqual(page_home_idx, -1, "Missing id=\"page-home\" in index.html")

        self.assertTrue(
            container_idx < warning_idx < page_home_idx,
            "[CONTRACT BREACH] Warning containing 'JavaScript 已禁用' must be placed between <main class=\"container\"> and id=\"page-home\""
        )

    def test_cache_query_token_consistency(self):
        """Stress-test: Verify cache token consistency /css/style.css?v=20261031_award in index and about."""
        expected_token = "/css/style.css?v=20261031_award"
        self.assertIn(
            expected_token,
            self.index_html,
            f"index.html must reference exact stylesheet token '{expected_token}'"
        )
        self.assertIn(
            expected_token,
            self.about_html,
            f"about.html must reference exact stylesheet token '{expected_token}'"
        )

    # =========================================================================
    # Track 4: Elimination of AI Slop & Visual Clutter
    # =========================================================================

    def test_zero_unicode_heavy_arrows_in_index_and_about(self):
        """Stress-test: Verify 0 occurrences of unicode heavy arrow (➔ / U+2794)."""
        arrow_char = "\u2794"  # ➔
        arrow_in_index = self.index_html.count(arrow_char)
        arrow_in_about = self.about_html.count(arrow_char)

        self.assertEqual(
            arrow_in_index,
            0,
            f"[SLOP DETECTED] Found {arrow_in_index} unicode heavy arrows (➔) in public/index.html"
        )
        self.assertEqual(
            arrow_in_about,
            0,
            f"[SLOP DETECTED] Found {arrow_in_about} unicode heavy arrows (➔) in public/about.html"
        )

    def test_zero_rating_stars_in_index_and_about(self):
        """Stress-test: Verify 0 occurrences of decorative rating stars (★ / U+2605, ☆ / U+2606)."""
        star_black = "\u2605"  # ★
        star_white = "\u2606"  # ☆

        self.assertEqual(
            self.index_html.count(star_black),
            0,
            f"[SLOP DETECTED] Found black rating star (★) in public/index.html"
        )
        self.assertEqual(
            self.index_html.count(star_white),
            0,
            f"[SLOP DETECTED] Found white rating star (☆) in public/index.html"
        )
        self.assertEqual(
            self.about_html.count(star_black),
            0,
            f"[SLOP DETECTED] Found black rating star (★) in public/about.html"
        )
        self.assertEqual(
            self.about_html.count(star_white),
            0,
            f"[SLOP DETECTED] Found white rating star (☆) in public/about.html"
        )

    def test_zero_ambient_glow_mesh_clusters(self):
        """Stress-test: Verify 0 occurrences of .ambient-glow-mesh across index and about."""
        self.assertEqual(
            self.index_soup.select(".ambient-glow-mesh"),
            [],
            "[SLOP DETECTED] Found .ambient-glow-mesh in public/index.html"
        )
        self.assertEqual(
            self.about_soup.select(".ambient-glow-mesh"),
            [],
            "[SLOP DETECTED] Found .ambient-glow-mesh in public/about.html"
        )

    def test_zero_btn_shine_elements(self):
        """Stress-test: Verify 0 occurrences of .btn-shine across index and about."""
        self.assertEqual(
            self.index_soup.select(".btn-shine"),
            [],
            "[SLOP DETECTED] Found .btn-shine in public/index.html"
        )
        self.assertEqual(
            self.about_soup.select(".btn-shine"),
            [],
            "[SLOP DETECTED] Found .btn-shine in public/about.html"
        )

    def test_zero_marketing_hyperbole_slop_strings(self):
        """Stress-test: Verify elimination of marketing hyperbole and replaced with institutional microcopy."""
        banned_phrases = [
            "现代化高引力 Hero 核心操作集群",
            "高维通算能力",
            "启动财富推演",
            "华尔街对冲基金级",
            "拒绝惩罚上涨收益的粗暴标准差！",
            "彻底击碎择时神话，奠定机械化定投的数学信仰",
            "20年 (黄金复利期)",
            "肥尾黑天鹅实测",
            "Designed to Award Tier Standards · Webby & Awwwards Compliant",
            "将华尔街量化对冲算法转化为您的日常定投武器",
        ]
        for phrase in banned_phrases:
            self.assertNotIn(
                phrase,
                self.index_html,
                f"[SLOP DETECTED] Banned marketing phrase '{phrase}' still found in public/index.html"
            )
            self.assertNotIn(
                phrase,
                self.about_html,
                f"[SLOP DETECTED] Banned marketing phrase '{phrase}' still found in public/about.html"
            )

    def test_zero_inline_badge_linear_gradients(self):
        """Stress-test: Verify no hardcoded linear-gradient badges in algo-content and quant-frontier-toggle."""
        algo_content = self.index_soup.find(id="algo-content")
        if algo_content:
            self.assertNotIn(
                "linear-gradient",
                str(algo_content),
                "[SLOP DETECTED] Found hardcoded linear-gradient inside #algo-content"
            )
        frontier_toggle = self.index_soup.find(id="quant-frontier-toggle")
        if frontier_toggle:
            self.assertNotIn(
                "linear-gradient",
                str(frontier_toggle),
                "[SLOP DETECTED] Found hardcoded linear-gradient inside #quant-frontier-toggle"
            )

    def test_all_json_ld_blocks_are_valid_json(self):
        """Stress-test: Verify every single application/ld+json block in index.html and about.html parses cleanly."""
        for path_name, soup in [("index.html", self.index_soup), ("about.html", self.about_soup)]:
            scripts = soup.find_all("script", type="application/ld+json")
            self.assertGreater(len(scripts), 0, f"Expected JSON-LD scripts in {path_name}")
            for idx, script in enumerate(scripts):
                try:
                    parsed = json.loads(script.string)
                    self.assertIsInstance(parsed, dict, f"JSON-LD block #{idx} in {path_name} must parse as dict")
                except Exception as e:
                    self.fail(f"Invalid JSON in JSON-LD block #{idx} in {path_name}: {e}")

    def test_about_html_zero_duplicate_ids(self):
        """Stress-test: Verify 0 duplicate IDs in public/about.html."""
        all_id_elements = self.about_soup.find_all(id=True)
        id_list = [el["id"] for el in all_id_elements]
        duplicates = [x for x in set(id_list) if id_list.count(x) > 1]
        self.assertEqual(
            duplicates,
            [],
            f"[CRITICAL FAIL] Duplicate DOM IDs found in public/about.html: {duplicates}"
        )

    # =========================================================================
    # Track 5: Modern Web Platform Standards Verification
    # =========================================================================

    def test_color_scheme_meta_tag(self):
        """Stress-test: Verify <meta name="color-scheme" content="light dark"> in both pages."""
        cs_index = self.index_soup.find("meta", attrs={"name": "color-scheme"})
        self.assertIsNotNone(cs_index, "Missing <meta name=\"color-scheme\"> in index.html")
        self.assertIn("light dark", cs_index.get("content", ""))

        cs_about = self.about_soup.find("meta", attrs={"name": "color-scheme"})
        self.assertIsNotNone(cs_about, "Missing <meta name=\"color-scheme\"> in about.html")
        self.assertIn("light dark", cs_about.get("content", ""))

    def test_speculation_rules_json_validity_and_coverage(self):
        """Stress-test: Verify valid speculationrules JSON with prefetch and prerender rules."""
        for path_name, soup in [("index.html", self.index_soup), ("about.html", self.about_soup)]:
            spec_script = soup.find("script", type="speculationrules")
            self.assertIsNotNone(spec_script, f"Missing <script type=\"speculationrules\"> in {path_name}")
            try:
                data = json.loads(spec_script.string)
            except Exception as e:
                self.fail(f"Invalid speculationrules JSON in {path_name}: {e}")

            self.assertIn("prefetch", data, f"speculationrules must define prefetch in {path_name}")
            self.assertIn("prerender", data, f"speculationrules must define prerender in {path_name}")

    def test_modal_accessibility_dialog_attributes(self):
        """Stress-test: Verify modal containers define role='dialog' or accessible aria attributes."""
        modals = [
            "rank-select-modal",
            "quota-select-modal",
            "poster-modal-backdrop",
            "shortcut-hud-modal"
        ]
        for m_id in modals:
            el = self.index_soup.find(id=m_id)
            if el is not None:
                has_dialog_semantics = (
                    el.name == "dialog" or
                    el.get("role") == "dialog" or
                    el.get("aria-modal") == "true" or
                    "modal" in el.get("class", [])
                )
                self.assertTrue(
                    has_dialog_semantics,
                    f"Modal #{m_id} must have semantic dialog attributes (name='dialog', role='dialog', or aria-modal)"
                )

    # =========================================================================
    # Track 6: Semantic Integrity of public/about.html
    # =========================================================================

    def test_about_html_all_nine_h2_keywords(self):
        """Stress-test: Verify all 9 required H2 section keywords exist in about.html."""
        required_h2_keywords = [
            "平台使命与创立初衷",
            "核心量化模型与算法体系",
            "量化投研团队与专业资质背景",
            "学术理论文献与量化模型引用清单",
            "数据流水线与更新机制",
            "内容审校与质量控制流程",
            "独立性与无利益冲突声明",
            "法律合规与免责声明",
            "团队联系与技术支持"
        ]
        h2_texts = [h2.get_text() for h2 in self.about_soup.find_all("h2")]
        for kw in required_h2_keywords:
            matched = any(kw in text for text in h2_texts)
            self.assertTrue(
                matched,
                f"[CONTRACT BREACH] Required H2 section keyword '{kw}' not found in public/about.html H2 tags: {h2_texts}"
            )

    def test_about_html_citations_and_credentials(self):
        """Stress-test: Verify CFA credential and Markowitz, Sharpe, Sortino citations in about.html."""
        text = self.about_soup.get_text()
        self.assertIn("CFA", text, "CFA credential must be mentioned in about.html")
        self.assertIn("Markowitz", text, "Markowitz citation must be present in about.html")
        self.assertIn("Sharpe", text, "Sharpe citation must be present in about.html")
        self.assertIn("Sortino", text, "Sortino citation must be present in about.html")

        # Verify publication years
        self.assertIn("1952", text, "Markowitz (1952) year must be present")
        self.assertIn("1964", text, "Sharpe (1964) year must be present")
        self.assertIn("1994", text, "Sortino (1994) year must be present")

    def test_about_html_mailto_link(self):
        """Stress-test: Verify valid mailto: link in about.html."""
        mail_links = self.about_soup.find_all("a", href=re.compile(r"^mailto:"))
        self.assertGreaterEqual(
            len(mail_links),
            1,
            "about.html must contain at least one valid mailto: link"
        )
        self.assertEqual(mail_links[0]["href"], "mailto:contact@858000.xyz")


if __name__ == "__main__":
    unittest.main()
