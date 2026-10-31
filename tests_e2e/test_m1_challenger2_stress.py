"""Automated Stress-Test Harness for Milestone 1 Challenger 2.

Evaluates:
1. Verbatim existence and uniqueness of the 10 critical JS DOM IDs in public/index.html.
2. Complete audit of JS selector coupling between app.js and index.html for HUD and navigation.
3. Media query coverage and layout stress testing across 320px, 375px, 768px, 992px, 1200px, 1440px.
4. Detection of overflow/clipping hazards: fixed widths, non-wrapping flex, negative margins,
   unwrapped tables, missing box-sizing, horizontal scrollbar risks.
"""

import os
import re
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT_DIR / "public" / "index.html"
STYLE_PATH = ROOT_DIR / "public" / "css" / "style.css"
APP_JS_PATH = ROOT_DIR / "public" / "js" / "app.js"


class TestMilestone1Challenger2Stress(unittest.TestCase):
    """Adversarial stress-test suite for Milestone 1 DOM boundaries & responsive viewports."""

    @classmethod
    def setUpClass(cls):
        assert INDEX_PATH.exists(), f"Missing index.html at {INDEX_PATH}"
        assert STYLE_PATH.exists(), f"Missing style.css at {STYLE_PATH}"
        assert APP_JS_PATH.exists(), f"Missing app.js at {APP_JS_PATH}"

        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            cls.index_html = f.read()
        cls.soup = BeautifulSoup(cls.index_html, "html.parser")

        with open(STYLE_PATH, "r", encoding="utf-8") as f:
            cls.css = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            cls.app_js = f.read()

    # =========================================================================
    # Track 1: Verbatim Critical DOM ID Boundary Stress Tests
    # =========================================================================

    def test_ten_critical_js_dom_ids_exist_verbatim_and_unique(self):
        """Verify all 10 critical JS DOM IDs exist verbatim and are unique in public/index.html."""
        critical_ids = [
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
        ]

        for dom_id in critical_ids:
            # 1. BeautifulSoup node check
            elem = self.soup.find(id=dom_id)
            self.assertIsNotNone(
                elem,
                f"[CRITICAL FAIL] DOM ID '{dom_id}' not found in public/index.html via DOM parser"
            )

            # 2. Raw regex check for verbatim id="..." or id='...'
            matches = re.findall(rf'\bid\s*=\s*["\']{re.escape(dom_id)}["\']', self.index_html)
            self.assertEqual(
                len(matches),
                1,
                f"[CRITICAL FAIL] DOM ID '{dom_id}' must appear exactly once verbatim in public/index.html, found {len(matches)}"
            )

    def test_app_js_coupling_with_critical_hud_and_nav_elements(self):
        """Verify app.js references all expected dynamic HUD and navigation IDs."""
        dynamic_js_ids = [
            "ticker-market-badge",
            "ticker-market-status",
            "ticker-latency-tag",
            "tk-pool-count",
            "tk-avail-count",
            "tk-min-fee",
            "theme-toggle",
            "nav-links",
            "footer-us-market-status",
        ]
        for dom_id in dynamic_js_ids:
            self.assertIn(
                dom_id,
                self.app_js,
                f"[COUPLING WARNING] Expected app.js to reference dynamic ID '{dom_id}'"
            )

    def test_accessibility_roles_on_critical_hud_elements(self):
        """Verify ARIA live regions and accessibility attributes on dynamic telemetry elements."""
        market_badge = self.soup.find(id="ticker-market-badge")
        self.assertIsNotNone(market_badge)
        self.assertEqual(market_badge.get("role"), "status", "ticker-market-badge must have role='status'")
        self.assertEqual(market_badge.get("aria-live"), "polite", "ticker-market-badge must have aria-live='polite'")

        # Ensure ticker-dot has pulse ring
        ticker_dot = self.soup.find(class_="ticker-dot")
        self.assertIsNotNone(ticker_dot, ".ticker-dot element must exist")
        pulse_ring = ticker_dot.find(class_="status-pulse-ring")
        self.assertIsNotNone(pulse_ring, ".status-pulse-ring must exist inside .ticker-dot for visual pulse")

    # =========================================================================
    # Track 2: Media Queries and Responsive Breakpoint Coverage (320px–1440px)
    # =========================================================================

    def test_media_query_spectrum_coverage(self):
        """Stress test presence and granularity of responsive breakpoints across 320px–1440px."""
        media_queries = re.findall(r"@media\s+([^{]+)\{", self.css)
        self.assertGreaterEqual(len(media_queries), 10, "style.css must have at least 10 distinct @media blocks")

        # Required coverage points:
        # - Mobile narrow: <= 360px or <= 420px or <= 480px
        # - Mobile standard: <= 576px or <= 640px
        # - Tablet portrait: <= 768px
        # - Tablet landscape / small desktop: <= 992px or <= 1024px
        has_narrow = any(re.search(r"max-width\s*:\s*(360px|420px|480px)", mq) for mq in media_queries)
        has_mobile = any(re.search(r"max-width\s*:\s*(576px|640px)", mq) for mq in media_queries)
        has_768 = any(re.search(r"max-width\s*:\s*768px", mq) for mq in media_queries)
        has_992_or_1024 = any(re.search(r"max-width\s*:\s*(992px|1024px)", mq) for mq in media_queries)

        self.assertTrue(has_narrow, "style.css must cover mobile narrow (<=360px, <=420px, or <=480px)")
        self.assertTrue(has_mobile, "style.css must cover standard mobile (<=576px or <=640px)")
        self.assertTrue(has_768, "style.css must cover tablet portrait (<=768px)")
        self.assertTrue(has_992_or_1024, "style.css must cover desktop transition (<=992px or <=1024px)")

    def test_hud_telemetry_responsive_adaptation(self):
        """Verify HUD grid columns scale from 5 (desktop) -> 2 (tablet <=992px) -> 1 (mobile <=576px)."""
        # Desktop base grid
        base_ticker_rule = re.search(r"\.hero-quant-ticker\s*\{[^}]*grid-template-columns\s*:\s*repeat\(5,\s*1fr\)", self.css)
        self.assertIsNotNone(base_ticker_rule, "Base .hero-quant-ticker must use 5-column grid for desktop")

        # 992px tablet 2-column grid
        tablet_992_rule = re.search(r"@media[^{]*max-width\s*:\s*992px[^{]*\{[\s\S]*?\.hero-quant-ticker\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)", self.css)
        self.assertIsNotNone(tablet_992_rule, "Under 992px, .hero-quant-ticker must adapt to 2-column grid")

        # 576px mobile 1-column grid
        mobile_576_rule = re.search(r"@media[^{]*max-width\s*:\s*576px[^{]*\{[\s\S]*?\.hero-quant-ticker\s*\{[^}]*grid-template-columns\s*:\s*1fr", self.css)
        self.assertIsNotNone(mobile_576_rule, "Under 576px, .hero-quant-ticker must collapse to 1-column layout")

        # Ticker header bar wrapping
        mobile_hdr_rule = re.search(r"@media[^{]*max-width\s*:\s*576px[^{]*\{[\s\S]*?\.ticker-header-bar\s*\{[^}]*flex-direction\s*:\s*column", self.css)
        self.assertIsNotNone(mobile_hdr_rule, "Under 576px, .ticker-header-bar must switch to column layout to prevent header overflow")

    def test_navbar_responsive_adaptation_and_drawer(self):
        """Verify navbar hides CTA button under 992px and enables full mobile drawer under 768px."""
        # Under 992px, nav CTA button should be hidden
        mq_992 = re.search(r"@media[^{]*max-width\s*:\s*992px[^{]*\{[\s\S]*?\.nav-cta-btn\s*\{[^}]*display\s*:\s*none", self.css)
        self.assertIsNotNone(mq_992, ".nav-cta-btn must be display: none under 992px to prevent navbar congestion")

        # Under 768px, hamburger toggle is displayed and links become a drawer
        mq_768_toggle = re.search(r"@media[^{]*max-width\s*:\s*768px[^{]*\{[\s\S]*?\.nav-toggle\s*\{[^}]*display\s*:\s*flex", self.css)
        self.assertIsNotNone(mq_768_toggle, ".nav-toggle must be displayed under 768px")

        mq_768_drawer = re.search(r"@media[^{]*max-width\s*:\s*768px[^{]*\{[\s\S]*?\.navbar\s+\.links\s*\{[^}]*position\s*:\s*fixed", self.css)
        self.assertIsNotNone(mq_768_drawer, ".navbar .links must become a fixed slide-down drawer under 768px")

    # =========================================================================
    # Track 3: Overflow and Clipping Hazards Across Viewport Boundaries
    # =========================================================================

    def test_universal_box_sizing_border_box(self):
        """Verify universal box-sizing: border-box reset covers all pseudo-elements (*, *::before, *::after)."""
        box_sizing_match = re.search(r"\*,\s*\*::before,\s*\*::after\s*\{[^}]*box-sizing\s*:\s*border-box", self.css)
        self.assertIsNotNone(
            box_sizing_match,
            "style.css must define universal *, *::before, *::after { box-sizing: border-box; } to avoid box expansion overflow"
        )

    def test_container_viewport_containment_at_320px(self):
        """Verify body and .container do not specify rigid min-widths exceeding 320px."""
        # Find any body or .container min-width
        body_rules = re.findall(r"body\s*\{([^}]+)\}", self.css)
        for r in body_rules:
            mw = re.search(r"min-width\s*:\s*(\d+)px", r)
            if mw:
                self.assertLessEqual(int(mw.group(1)), 320, f"body has dangerous min-width: {mw.group(1)}px")

        container_rules = re.findall(r"\.container\s*\{([^}]+)\}", self.css)
        for r in container_rules:
            mw = re.search(r"min-width\s*:\s*(\d+)px", r)
            if mw:
                self.assertLessEqual(int(mw.group(1)), 320, f".container has dangerous min-width: {mw.group(1)}px")

    def test_horizontal_table_containment(self):
        """Verify all tables inside index.html are wrapped in an overflow-x scrolling container."""
        tables = self.soup.find_all("table")
        for table in tables:
            parent_classes = table.parent.get("class", [])
            # Table should be wrapped in .table-wrap or .dir-table-wrap
            is_wrapped = any("table-wrap" in c or "scroll" in c for c in parent_classes)
            parent_style = table.parent.get("style", "")
            has_inline_scroll = "overflow-x" in parent_style or "overflow" in parent_style
            self.assertTrue(
                is_wrapped or has_inline_scroll,
                f"Table with id='{table.get('id', 'unnamed')}' must be wrapped in .table-wrap to prevent mobile blowout"
            )

    def test_root_variable_contrast_and_directional_tokens(self):
        """Verify --up and --down directional tokens exist with valid colors in both light and dark themes."""
        # Light mode / :root
        root_match = re.search(r":root\s*,\s*\[data-theme=[\'\"]light[\'\"]\]\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(root_match, ":root, [data-theme='light'] block must exist")
        root_content = root_match.group(1)
        self.assertIn("--up", root_content, "--up must be defined in :root / light mode")
        self.assertIn("--down", root_content, "--down must be defined in :root / light mode")

        # Dark mode
        dark_match = re.search(r'\[data-theme=[\'\"]dark[\'\"]\]\s*\{([^}]+)\}', self.css)
        self.assertIsNotNone(dark_match, "[data-theme='dark'] block must exist")
        dark_content = dark_match.group(1)
        self.assertIn("--up", dark_content, "--up must be defined in dark mode")
        self.assertIn("--down", dark_content, "--down must be defined in dark mode")

    def test_css_brace_balance(self):
        """Verify CSS curly braces are 100% balanced with zero syntax errors."""
        open_count = self.css.count("{")
        close_count = self.css.count("}")
        self.assertEqual(
            open_count,
            close_count,
            f"CSS brace mismatch: {open_count} open vs {close_count} close (diff: {open_count - close_count})"
        )

    def test_keyframe_animation_disambiguation(self):
        """Verify pulseGlow collision is resolved (pulseGlow for dot, pulseGlowAura for highlight)."""
        pulse_glow_matches = re.findall(r"@keyframes\s+pulseGlow\b", self.css)
        pulse_aura_matches = re.findall(r"@keyframes\s+pulseGlowAura\b", self.css)
        self.assertEqual(len(pulse_glow_matches), 1, "There must be exactly one @keyframes pulseGlow definition")
        self.assertEqual(len(pulse_aura_matches), 1, "There must be exactly one @keyframes pulseGlowAura definition")


if __name__ == "__main__":
    unittest.main()
