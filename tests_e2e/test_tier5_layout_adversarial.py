"""Tier 5 Adversarial Coverage Hardening: Layout Containment, Multi-Viewport, CSS Design System & SEO Sync.

Covers:
1. Multi-viewport boundary stress (320px to 2560px, overflow-x containment, max-width bounds).
2. Table touch-scrolling containment (.table-wrap, .dir-table-wrap, overflow-x: auto, -webkit-overflow-scrolling).
3. Cache-busting query synchronization (?v=20261031_award, detection of public/index.html line 164 gap).
4. CSS custom property contract & balance (light/dark mode token parity, brace balance, missing variable fallback analysis).
5. scraper/generate_seo.py Windows file-locking resilience (shutil.rmtree PermissionError [WinError 32] reproduction).
"""

import glob
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

from tests_e2e.e2e_common import (
    PROJECT_ROOT, PUBLIC_DIR, INDEX_HTML, ABOUT_HTML, STYLE_CSS,
    ARTICLES_DIR, FUND_PAGES_DIR, SITEMAP_XML,
    load_index_soup, load_about_soup, load_style_css,
    get_article_files, get_fund_page_files, check_css_balanced_braces
)


class TestMultiViewportBoundaryStress(unittest.TestCase):
    """Test multi-viewport boundary conditions from 320px (iPhone SE) to 2560px (ultra-wide 4K)."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_style_css()
        cls.index_soup = load_index_soup()
        cls.about_soup = load_about_soup()
        cls.article_files = get_article_files()
        cls.fund_files = get_fund_page_files()

    def test_viewport_meta_tag_across_all_archetypes(self):
        """TC 5.1: Confirm <meta name='viewport' content='width=device-width,initial-scale=1.0'> on all archetypes."""
        archetypes = [
            ("index.html", INDEX_HTML),
            ("about.html", ABOUT_HTML),
            ("sample_article", self.article_files[0]),
            ("sample_fund", self.fund_files[0]),
        ]
        for name, path in archetypes:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            meta = soup.find("meta", attrs={"name": "viewport"})
            self.assertIsNotNone(meta, f"Missing viewport meta tag in {name} ({path.name})")
            content = meta.get("content", "").replace(" ", "")
            self.assertIn("width=device-width", content, f"width=device-width missing in {name}")
            self.assertIn("initial-scale=1", content, f"initial-scale missing in {name}")

    def test_extreme_viewports_media_queries(self):
        """TC 5.2: Verify responsive media query definitions covering mobile (<768px) and tablet (<1024px)."""
        mobile_queries = re.findall(r"@media\s*\([^\)]*max-width\s*:\s*(768px|48rem)", self.css)
        tablet_queries = re.findall(r"@media\s*\([^\)]*max-width\s*:\s*(1024px|64rem)", self.css)
        self.assertGreater(len(mobile_queries), 0, "style.css must define mobile breakpoint (768px) queries")
        self.assertGreater(len(tablet_queries), 0, "style.css must define tablet breakpoint (1024px) queries")

    def test_root_html_body_overflow_containment(self):
        """TC 5.3: Verify html/body sets overflow-x: hidden to prevent horizontal viewport blowout."""
        # Find html rule
        html_rules = re.findall(r"(?<![a-zA-Z0-9_\-])html\s*\{([^}]+)\}", self.css)
        has_overflow_x = any("overflow-x:hidden" in r.replace(" ", "") for r in html_rules)
        self.assertTrue(has_overflow_x, "html must configure overflow-x: hidden to lock horizontal scrolling")

    def test_container_max_width_restraints(self):
        """TC 5.4: Verify .container and subpage containers clamp max-width to prevent ultra-wide stretching."""
        container_rules = re.findall(r"\.container[^{]*\{([^}]+)\}", self.css)
        self.assertTrue(any("max-width" in r for r in container_rules),
                        ".container must define max-width to contain layout on 1440px/1920px/2560px")

        # Check fund detail container
        fund_container_rules = re.findall(r"\.fund-detail-container[^{]*\{([^}]+)\}", self.css)
        self.assertTrue(any("max-width" in r for r in fund_container_rules),
                        ".fund-detail-container must define max-width")

    def test_grid_flex_wrapping_prevents_overflow(self):
        """TC 5.5: Verify multi-item card and button grids employ flex-wrap or auto-fit grid."""
        stripped = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)
        has_flex_wrap = "flex-wrap: wrap" in stripped or "flex-wrap:wrap" in stripped
        has_auto_grid = "repeat(auto-fit" in stripped or "repeat(auto-fill" in stripped
        self.assertTrue(has_flex_wrap, "style.css must utilize flex-wrap for fluid card wrapping")
        self.assertTrue(has_auto_grid, "style.css must utilize auto-fit/auto-fill grid systems")


class TestTableTouchScrollingContainment(unittest.TestCase):
    """Test mobile touch-scrolling containment across articles, fund detail pages, and index."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_style_css()
        cls.index_soup = load_index_soup()
        cls.article_files = get_article_files()
        cls.fund_files = get_fund_page_files()

    def test_article_tables_wrapped_in_table_wrap(self):
        """TC 5.6: Verify 100% of tables across all articles are wrapped in .table-wrap."""
        unwrapped = []
        for apath in self.article_files:
            with open(apath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            tables = soup.find_all("table")
            for t in tables:
                parent = t.parent
                classes = parent.get("class", [])
                if "table-wrap" not in classes:
                    unwrapped.append((apath.name, parent.name, classes))
        self.assertEqual(len(unwrapped), 0,
                         f"Found unwrapped tables in research articles: {unwrapped}")

    def test_fund_pages_tables_wrapped_in_dir_table_wrap(self):
        """TC 5.7: Verify 100% of tables in fund detail pages are wrapped in .dir-table-wrap."""
        unwrapped = []
        for fpath in self.fund_files:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            tables = soup.find_all("table")
            for t in tables:
                parent = t.parent
                classes = parent.get("class", [])
                if "dir-table-wrap" not in classes:
                    unwrapped.append((fpath.name, parent.name, classes))
        self.assertEqual(len(unwrapped), 0,
                         f"Found unwrapped tables in fund detail pages: {unwrapped}")

    def test_index_tables_enclosed_in_scrolling_wrappers(self):
        """TC 5.8: Verify all 8 tables in public/index.html have horizontal scrolling wrapper classes."""
        tables = self.index_soup.find_all("table")
        self.assertGreater(len(tables), 0, "index.html must contain quantitative tables")
        allowed_wrapper_classes = {"table-wrap", "dir-table-wrap", "quota-table-wrap"}
        for i, t in enumerate(tables):
            parent = t.parent
            parent_classes = set(parent.get("class", []))
            self.assertTrue(
                bool(parent_classes & allowed_wrapper_classes),
                f"Table #{i} (id={t.get('id')}) is not enclosed in an approved scrolling wrapper. Parent: {parent.name}.{parent_classes}"
            )

    def test_table_wrap_css_touch_scroll_properties(self):
        """TC 5.9: Verify .table-wrap and .dir-table-wrap define overflow-x: auto and -webkit-overflow-scrolling: touch."""
        # Check .table-wrap
        table_wrap_rules = re.findall(r"\.table-wrap\s*\{([^}]+)\}", self.css)
        self.assertTrue(any("overflow-x" in r for r in table_wrap_rules),
                        ".table-wrap must define overflow-x: auto")
        self.assertTrue(any("-webkit-overflow-scrolling" in r for r in table_wrap_rules),
                        ".table-wrap must define -webkit-overflow-scrolling: touch for iOS momentum scrolling")

        # Check .dir-table-wrap
        dir_rules = re.findall(r"\.dir-table-wrap\s*\{([^}]+)\}", self.css)
        self.assertTrue(any("overflow-x" in r for r in dir_rules),
                        ".dir-table-wrap must define overflow-x: auto")
        self.assertTrue(any("-webkit-overflow-scrolling" in r for r in dir_rules),
                        ".dir-table-wrap must define -webkit-overflow-scrolling: touch")

    def test_table_mobile_swipe_hints_and_view_toggle(self):
        """TC 5.10: Verify mobile swipe hints (.mobile-swipe-hint) and dual view classes exist in CSS."""
        self.assertIn(".mobile-swipe-hint", self.css, "style.css must style .mobile-swipe-hint")
        self.assertIn(".table-wrap.view-hidden", self.css, "style.css must support view-hidden on .table-wrap")


class TestCacheBustingQuerySynchronization(unittest.TestCase):
    """Test site-wide stylesheet cache-busting query synchronization and identify gaps."""

    CANONICAL_AWARD_TOKEN = "20261031_award"
    LEGACY_INDEX_TOKEN = "20261030_v1"

    @classmethod
    def setUpClass(cls):
        cls.article_files = get_article_files()
        cls.fund_files = get_fund_page_files()

    def test_subpages_cache_busting_sync_award_token(self):
        """TC 5.11: Verify about.html, 18 articles, and 60 fund detail pages use /css/style.css?v=20261031_award."""
        pages_to_verify = [ABOUT_HTML] + self.article_files + self.fund_files
        mismatched = []

        for p in pages_to_verify:
            with open(p, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            link = soup.find("link", rel=lambda r: r and "stylesheet" in r, href=lambda h: h and "style.css" in h)
            if not link:
                mismatched.append((p.name, "missing style.css link"))
                continue
            href = link.get("href", "")
            if f"v={self.CANONICAL_AWARD_TOKEN}" not in href:
                mismatched.append((p.name, href))

        self.assertEqual(len(mismatched), 0,
                         f"Subpages failing canonical cache-busting token (?v={self.CANONICAL_AWARD_TOKEN}): {mismatched[:5]}")

    def test_detect_index_cache_busting_desync_line_164(self):
        """TC 5.12: Verify public/index.html line 164 is synchronized with canonical award cache token."""
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Locate style.css link in index.html
        found_line = None
        found_content = ""
        for idx, line in enumerate(lines):
            if "rel=\"stylesheet\"" in line and "style.css" in line:
                found_line = idx + 1
                found_content = line.strip()
                break

        self.assertIsNotNone(found_line, "public/index.html must contain a stylesheet link to style.css")
        # Line 164 is the known location
        self.assertEqual(found_line, 164, f"Expected stylesheet link on line 164, found on line {found_line}")
        # Verify synchronized token and leading root slash
        self.assertIn(f"v={self.CANONICAL_AWARD_TOKEN}", found_content,
                      f"Line 164 must be synchronized with award token v={self.CANONICAL_AWARD_TOKEN}")
        self.assertIn('href="/css/style.css', found_content,
                      "Line 164 must use leading root slash /css/style.css")

    def test_legal_pages_cache_busting_queries(self):
        """TC 5.13: Document terms-of-service and privacy-policy cache-busting queries."""
        legal_pages = [
            PUBLIC_DIR / "terms-of-service.html",
            PUBLIC_DIR / "privacy-policy.html"
        ]
        for lp in legal_pages:
            if lp.exists():
                with open(lp, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f.read(), "html.parser")
                link = soup.find("link", rel=lambda r: r and "stylesheet" in r, href=lambda h: h and "style.css" in h)
                self.assertIsNotNone(link, f"{lp.name} must include stylesheet link")
                # Document legacy version v=20261009_v7
                self.assertIn("?v=", link.get("href", ""), f"{lp.name} should specify cache query")


class TestCSSCustomPropertyContractAndBalance(unittest.TestCase):
    """Test CSS design system custom properties, light/dark parity, and brace balance."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_style_css()
        cls.stripped = re.sub(r"/\*.*?\*/", "", cls.css, flags=re.DOTALL)

    def test_css_brace_and_comment_balance(self):
        """TC 5.14: Verify complete curly brace balance across style.css."""
        ok, msg = check_css_balanced_braces(self.css)
        self.assertTrue(ok, f"CSS syntax error: {msg}")

    def test_critical_tokens_in_light_and_dark_themes(self):
        """TC 5.15: Verify critical tokens (--up, --down, --table-hover-bg, --surface, --txt, etc.) exist in light & dark."""
        root_chunk = re.search(r":root[^{]*\{([^}]+)\}", self.stripped)
        dark_chunk = re.search(r'\[data-theme=["\']dark["\']\]\s*\{([^}]+)\}', self.stripped)

        self.assertIsNotNone(root_chunk, ":root / light theme block must exist in style.css")
        self.assertIsNotNone(dark_chunk, "[data-theme='dark'] block must exist in style.css")

        root_vars = set(re.findall(r"(--[a-zA-Z0-9_\-]+)\s*:", root_chunk.group(1)))
        dark_vars = set(re.findall(r"(--[a-zA-Z0-9_\-]+)\s*:", dark_chunk.group(1)))

        critical_tokens = [
            "--up", "--down", "--table-hover-bg", "--surface",
            "--txt", "--border", "--accent", "--bg", "--bg2", "--card"
        ]
        for token in critical_tokens:
            self.assertIn(token, root_vars, f"Critical token {token} missing in :root / light theme")
            self.assertIn(token, dark_vars, f"Critical token {token} missing in [data-theme='dark']")

    def test_financial_delta_color_contrast_tokens(self):
        """TC 5.16: Verify semantic financial delta tokens (--up, --down) have valid distinct hex codes in both themes."""
        # Light mode
        root_chunk = re.search(r":root[^{]*\{([^}]+)\}", self.stripped).group(1)
        up_light = re.search(r"--up\s*:\s*([^;]+);", root_chunk).group(1).strip()
        down_light = re.search(r"--down\s*:\s*([^;]+);", root_chunk).group(1).strip()

        # Dark mode
        dark_chunk = re.search(r'\[data-theme=["\']dark["\']\]\s*\{([^}]+)\}', self.stripped).group(1)
        up_dark = re.search(r"--up\s*:\s*([^;]+);", dark_chunk).group(1).strip()
        down_dark = re.search(r"--down\s*:\s*([^;]+);", dark_chunk).group(1).strip()

        # Both must be non-empty and different from each other
        self.assertNotEqual(up_light, down_light, "Light --up and --down must not be identical")
        self.assertNotEqual(up_dark, down_dark, "Dark --up and --down must not be identical")
        self.assertNotEqual(up_light, up_dark, "Dark --up should use enhanced high-contrast green")
        self.assertNotEqual(down_light, down_dark, "Dark --down should use enhanced high-contrast red")

    def test_referenced_css_variables_and_fallback_contract(self):
        """TC 5.17: White-box analysis of referenced variables. Verifies --shadow-md definition and fallback."""
        all_defs = set(re.findall(r"(--[a-zA-Z0-9_\-]+)\s*:", self.stripped))
        # Verify --shadow-md is properly declared in design system tokens
        self.assertIn("--shadow-md", all_defs, "--shadow-md must be defined in style.css custom properties")
        # Line 13077 uses box-shadow: var(--shadow-md, var(--shadow)); with fallback
        metric_card_hover = re.search(r"\.fund-metric-card:hover\s*\{([^}]+)\}", self.stripped)
        self.assertIsNotNone(metric_card_hover, ".fund-metric-card:hover rule must exist")
        self.assertIn("var(--shadow-md", metric_card_hover.group(1),
                      ".fund-metric-card:hover must reference --shadow-md")
        self.assertIn("var(--shadow)", metric_card_hover.group(1),
                      ".fund-metric-card:hover must provide var(--shadow) fallback")

    def test_fluid_typography_clamp_validity(self):
        """TC 5.18: Verify fluid typography tokens declare syntactically valid clamp() expressions."""
        root_chunk = re.search(r":root[^{]*\{([^}]+)\}", self.stripped).group(1)
        clamp_tokens = ["--font-size-hero", "--font-size-h1", "--font-size-body"]
        for ct in clamp_tokens:
            m = re.search(rf"{ct}\s*:\s*clamp\(([^)]+)\);", root_chunk)
            self.assertIsNotNone(m, f"{ct} must use clamp() expression")
            args = [a.strip() for a in m.group(1).split(",")]
            self.assertEqual(len(args), 3, f"{ct} clamp must have exactly 3 arguments (min, val, max)")


class TestSEOGeneratorFileLockingResilience(unittest.TestCase):
    """Adversarial stress testing of scraper/generate_seo.py Windows file-locking behavior."""

    def test_shutil_rmtree_vulnerability_under_active_read_lock(self):
        """TC 5.19: Verify scraper/generate_seo.py resilience against Windows file-locking under active read handle."""
        target_file = PUBLIC_DIR / "fund" / "000834.html"
        self.assertTrue(target_file.exists(), "Target fund page 000834.html must exist before lock stress test")

        # Open file in read mode to simulate concurrent reader (e.g., local server or crawler)
        with open(target_file, "r", encoding="utf-8") as locked_handle:
            # Execute scraper/generate_seo.py as a subprocess
            res = subprocess.run(
                [sys.executable, "scraper/generate_seo.py"],
                capture_output=True,
                cwd=str(PROJECT_ROOT)
            )

        # On Windows, generate_seo.py must successfully complete even under concurrent read lock
        self.assertEqual(
            res.returncode, 0,
            f"Expected generate_seo.py to exit 0 under concurrent Windows read lock, got {res.returncode}: {res.stderr.decode('cp936', errors='replace')}"
        )
        self.assertTrue((PUBLIC_DIR / "fund" / "000834.html").exists(), "Target file must exist after generation")

    def test_generate_seo_post_failure_state_restoration(self):
        """TC 5.20: Verify that running generate_seo.py without active locks cleanly generates all 60 fund pages."""
        res = subprocess.run(
            [sys.executable, "scraper/generate_seo.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(res.returncode, 0, f"Clean execution of generate_seo.py failed: {res.stderr}")
        generated_pages = list((PUBLIC_DIR / "fund").glob("*.html"))
        self.assertEqual(len(generated_pages), 60, f"Expected exactly 60 fund pages after generation, found {len(generated_pages)}")


if __name__ == "__main__":
    unittest.main()
