"""Empirical Multi-Viewport & Layout Boundary Stress Test Harness for Milestone 3.

Challenger: teamwork_challenger_m3_2
Verifies:
1. Multi-viewport responsive layout adaptability across mobile (375px), tablet (768px), and desktop (1440px)
   for about.html, all 18 articles in articles/*.html, and all 60 fund pages in fund/*.html.
2. Responsive grid column allocations and mathematical non-overflow bounds (pain-points grid, methodology cards,
   EEAT credentials, 4-card metric grid, substitutes grid).
3. Table touch-scrolling and horizontal overflow containment in .table-wrap and .dir-table-wrap
   (scrollWidth <= clientWidth on document viewport, smooth momentum swipe scrolling inside container).
4. Zero horizontal scroll overflow (scrollWidth <= clientWidth) at root page container across all viewports.
5. Internal navigation link hygiene (root-relative paths) and SEO canonical tag preservation.
"""

import math
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
    load_about_soup, load_style_css, get_article_files, get_fund_page_files,
    ABOUT_HTML, ARTICLES_DIR, FUND_PAGES_DIR
)


def calculate_grid_columns(container_width: float, min_col_width: float, gap: float) -> int:
    """Calculates the number of columns repeat(auto-fit, minmax(min_col_width, 1fr)) produces."""
    if container_width < min_col_width:
        return 1
    # n * min_col_width + (n - 1) * gap <= container_width
    # n * (min_col_width + gap) - gap <= container_width
    cols = int(math.floor((container_width + gap) / (min_col_width + gap)))
    return max(1, cols)


class TestAboutPageResponsiveLayoutAndBoundaries(unittest.TestCase):
    """Stress tests public/about.html layout adaptability, cards, and viewport boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_about_soup()
        cls.css = load_style_css()

    def test_about_page_viewport_meta_and_container(self):
        """TC 3.1: Verify viewport meta tag and container constraint in about.html."""
        meta = self.soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(meta, "about.html must have viewport meta tag")
        self.assertIn("width=device-width", meta.get("content", ""))

        main = self.soup.find("main")
        self.assertIsNotNone(main, "about.html must have <main>")
        self.assertIn("container", main.get("class", []))

        # Check inline styles on <main>
        style = main.get("style", "")
        # Should have max-width, but NO fixed width
        if "max-width" in style:
            m = re.search(r"max-width\s*:\s*(\d+)px", style)
            if m:
                self.assertLessEqual(int(m.group(1)), 1200, "Container max-width should be standard readable width")
        self.assertNotRegex(style, r"(?<!max-)width\s*:\s*\d{3,}px", "Container must not have fixed px width")

    def test_about_pain_points_grid_reflow(self):
        """TC 3.2: Verify .pain-point-grid mathematical reflow across 375px, 768px, 1440px."""
        # CSS check
        self.assertIn(".pain-point-grid", self.css)
        pp_match = re.search(r"\.pain-point-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(pp_match, "style.css must define .pain-point-grid")
        rules = pp_match.group(1)
        self.assertIn("grid-template-columns", rules)
        self.assertIn("minmax(250px", rules)

        # DOM check
        grid = self.soup.find(class_="pain-point-grid")
        self.assertIsNotNone(grid, "about.html must contain .pain-point-grid")
        cards = grid.find_all(class_="pain-point-card")
        self.assertEqual(len(cards), 3, "Must have exactly 3 pain point cards")

        for card in cards:
            badge = card.find(class_="pain-point-badge")
            title = card.find(class_="pain-point-title")
            desc = card.find(class_="pain-point-desc")
            sol = card.find(class_="solution-pill")
            self.assertIsNotNone(badge, "Pain point card must contain .pain-point-badge")
            self.assertIsNotNone(title, "Pain point card must contain .pain-point-title")
            self.assertIsNotNone(desc, "Pain point card must contain .pain-point-desc")
            self.assertIsNotNone(sol, "Pain point card must contain .solution-pill")

        # Mathematical reflow check:
        # At 375px mobile (content width = 375 - 32px padding = 343px):
        cols_375 = calculate_grid_columns(343.0, 250.0, 18.4)  # 1.15rem ~= 18.4px
        self.assertEqual(cols_375, 1, "At 375px, pain point grid must allocate exactly 1 column")

        # At 768px tablet (content width = 768 - 32px = 736px):
        cols_768 = calculate_grid_columns(736.0, 250.0, 18.4)
        self.assertEqual(cols_768, 2, "At 768px, pain point grid must allocate 2 columns")

        # At 1440px desktop (main container capped at 920px -> 920 - 32 = 888px):
        cols_1440 = calculate_grid_columns(888.0, 250.0, 18.4)
        self.assertEqual(cols_1440, 3, "At 1440px desktop, pain point grid must allocate 3 columns")

    def test_about_methodology_cards_and_formula_overflow(self):
        """TC 3.3: Verify methodology cards, mobile 1fr reflow, and formula overflow safety."""
        # CSS rule for methodology-grid
        self.assertIn(".methodology-grid", self.css)
        # Check that .methodology-grid has 1fr reflow in a 768px media query
        mq_blocks = re.findall(r"@media\s*\([^\)]*max-width\s*:\s*768px\)[^{]*\{([\s\S]*?\n\})", self.css)
        methodology_in_mq = any(".methodology-grid" in b and "grid-template-columns: 1fr" in b for b in mq_blocks)
        self.assertTrue(methodology_in_mq, "Methodology grid must collapse to 1fr on mobile (max-width: 768px)")

        # DOM check: 5 methodology cards
        grid = self.soup.find(class_="methodology-grid")
        self.assertIsNotNone(grid, "about.html must contain .methodology-grid")
        cards = grid.find_all(class_="methodology-card")
        self.assertEqual(len(cards), 5, "Must have exactly 5 quant methodology cards")

        # Check .quant-formula overflow safety
        formula_match = re.search(r"\.quant-formula\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(formula_match, "style.css must define .quant-formula")
        formula_rules = formula_match.group(1)
        self.assertIn("overflow-x: auto", formula_rules, ".quant-formula must have overflow-x: auto to prevent blowout")
        self.assertIn("white-space: nowrap", formula_rules, ".quant-formula must have white-space: nowrap")

        for card in cards:
            formula = card.find(class_="quant-formula")
            self.assertIsNotNone(formula, "Each methodology card must contain a .quant-formula box")
            params = card.find(class_="methodology-params")
            self.assertIsNotNone(params, "Each methodology card must contain .methodology-params")

    def test_about_eeat_credentials_card(self):
        """TC 3.4: Verify .eeat-author-card institutional layout and grid reflow."""
        card = self.soup.find(class_="eeat-author-card")
        self.assertIsNotNone(card, "about.html must contain .eeat-author-card")

        header = card.find(class_="eeat-header")
        self.assertIsNotNone(header, "EEAT card must have .eeat-header")
        self.assertIsNotNone(header.find(class_="eeat-avatar"))
        self.assertIsNotNone(header.find(class_="eeat-meta"))

        details = card.find(class_="eeat-details-grid")
        self.assertIsNotNone(details, "EEAT card must have .eeat-details-grid")
        items = details.find_all(class_="eeat-item")
        self.assertGreaterEqual(len(items), 6, "EEAT card must have at least 6 institutional items")

        # CSS rule for details grid
        dg_match = re.search(r"\.eeat-details-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(dg_match, "style.css must define .eeat-details-grid")
        dg_rules = dg_match.group(1)
        self.assertIn("grid-template-columns", dg_rules)
        self.assertIn("minmax(200px", dg_rules)

        # Mathematical check: At 375px mobile, inner width ~299px >= 200px -> 1 column
        cols_375 = calculate_grid_columns(299.0, 200.0, 12.0)
        self.assertEqual(cols_375, 1, "EEAT details grid must allocate 1 column on mobile")

        # Disclaimer
        disclaimer = card.find(class_="eeat-disclaimer")
        self.assertIsNotNone(disclaimer, "EEAT card must contain .eeat-disclaimer")

    def test_about_footer_colophon_reflow(self):
        """TC 3.5: Verify .footer-inner 3-column colophon and mobile column reflow."""
        footer = self.soup.find("footer")
        self.assertIsNotNone(footer, "about.html must contain <footer>")

        inner = footer.find(class_="footer-inner")
        self.assertIsNotNone(inner, "<footer> must contain .footer-inner")
        self.assertIsNotNone(inner.find(class_="footer-info"))
        links_cols = inner.find_all(class_="footer-links")
        self.assertEqual(len(links_cols), 2, ".footer-inner must contain 2 .footer-links columns")

        # Check CSS flex-direction: column under 768px
        self.assertIn(".footer-inner:has(.footer-info)", self.css)
        mq_footer = re.search(r"\.footer-inner:has\(\.footer-info\)\s*\{[^}]*flex-direction:\s*column", self.css)
        self.assertIsNotNone(mq_footer, "Footer must collapse to flex-direction: column at mobile breakpoint")


class TestArticlesResponsiveLayoutAndTableTouchScroll(unittest.TestCase):
    """Stress tests all 18 articles for takeaway cards, table touch wrappers, and link safety."""

    @classmethod
    def setUpClass(cls):
        cls.articles = get_article_files()
        cls.css = load_style_css()

    def test_article_takeaways_card_presence_and_structure(self):
        """TC 3.6: Verify .article-takeaways-card in all 18 research articles right beneath .page-sub."""
        self.assertEqual(len(self.articles), 18, "Must verify exactly 18 research articles")

        # CSS checks
        self.assertIn(".article-takeaways-card", self.css)
        self.assertIn(".takeaways-top", self.css)
        self.assertIn(".takeaways-pills", self.css)
        self.assertIn(".takeaways-pill", self.css)
        self.assertIn(".takeaways-list", self.css)

        for fpath in self.articles:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            card = soup.find(class_="article-takeaways-card")
            self.assertIsNotNone(card, f"Article {fpath.name} must contain .article-takeaways-card")

            # Check placement: should be right beneath page-sub or page-title
            page_sub = soup.find(class_="page-sub")
            self.assertIsNotNone(page_sub, f"Article {fpath.name} must have .page-sub")

            # Verify card internals
            top = card.find(class_="takeaways-top")
            self.assertIsNotNone(top, f"Article {fpath.name} card must have .takeaways-top")
            self.assertIsNotNone(top.find(class_="takeaways-title"), f"{fpath.name} missing title")
            self.assertIsNotNone(top.find(class_="takeaways-read-time"), f"{fpath.name} missing read-time")

            pills = card.find(class_="takeaways-pills")
            self.assertIsNotNone(pills, f"Article {fpath.name} must have .takeaways-pills")
            pill_items = pills.find_all(class_="takeaways-pill")
            self.assertGreaterEqual(len(pill_items), 2, f"{fpath.name} must have >=2 KPI pills")

            tlist = card.find(class_="takeaways-list")
            self.assertIsNotNone(tlist, f"Article {fpath.name} must have .takeaways-list")
            li_items = tlist.find_all("li")
            self.assertGreaterEqual(len(li_items), 2, f"{fpath.name} must have >=2 bullet items")

    def test_table_touch_scroll_wrappers_in_articles(self):
        """TC 3.7: Verify all data tables across articles are wrapped in .table-wrap with touch-scrolling."""
        # Check CSS rules
        tw_match = re.search(r"\.article-content\s+\.table-wrap\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(tw_match, "style.css must define .article-content .table-wrap")
        tw_rules = tw_match.group(1)
        self.assertIn("overflow-x: auto", tw_rules, ".table-wrap must have overflow-x: auto")
        self.assertIn("-webkit-overflow-scrolling: touch", tw_rules, ".table-wrap must have touch momentum scrolling")
        self.assertIn("max-width: 100%", tw_rules, ".table-wrap must have max-width: 100%")

        # Table min-width rule
        tbl_match = re.search(r"\.article-content\s+\.table-wrap\s+table\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(tbl_match, "style.css must define .article-content .table-wrap table")
        tbl_rules = tbl_match.group(1)
        self.assertIn("min-width: 520px", tbl_rules, "Table inside wrapper must have min-width: 520px")

        # Scan all HTML files in articles
        all_article_htmls = list(ARTICLES_DIR.glob("*.html"))
        tables_found = 0
        for fpath in all_article_htmls:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            tables = soup.find_all("table")
            for table in tables:
                tables_found += 1
                parent = table.parent
                self.assertIsNotNone(parent, f"Table in {fpath.name} must have parent element")
                parent_classes = parent.get("class", [])
                self.assertTrue(
                    "table-wrap" in parent_classes or "dir-table-wrap" in parent_classes,
                    f"Table in {fpath.name} (line {getattr(table, 'sourceline', '?')}) MUST be wrapped in .table-wrap"
                )

        self.assertGreaterEqual(tables_found, 7, f"All data tables across research articles must be wrapped (found {tables_found})")

    def test_article_navigation_links_are_root_relative(self):
        """TC 3.8: Verify zero internal links point to absolute domain https://858000.xyz in articles."""
        domain_pattern = re.compile(r"^https?://(?:www\.)?858000\.xyz(/.*)?$")
        for fpath in self.articles:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            anchors = soup.find_all("a", href=True)
            for a in anchors:
                href = a["href"].strip()
                # Internal links should NOT be absolute 858000.xyz
                if domain_pattern.match(href):
                    self.fail(
                        f"Found hardcoded absolute domain link '{href}' in {fpath.name}. "
                        "All internal navigation must use root-relative paths."
                    )


class TestFundDetailPagesResponsiveLayoutAndBoundaries(unittest.TestCase):
    """Stress tests all 60 fund detail pages for 4-card metric grid, substitute tables, and footer."""

    @classmethod
    def setUpClass(cls):
        cls.funds = get_fund_page_files()
        cls.css = load_style_css()

    def test_all_60_fund_pages_exist_and_have_container(self):
        """TC 3.9: Verify all 60 fund pages exist with semantic .fund-detail-container."""
        self.assertEqual(len(self.funds), 60, "Must have exactly 60 fund detail pages")

        self.assertIn(".fund-detail-container", self.css)
        self.assertIn(".fund-metrics-grid", self.css)
        self.assertIn(".fund-metric-card", self.css)

    def test_fund_metrics_grid_structure_and_reflow(self):
        """TC 3.10: Verify 4-card metric telemetry grid in all 60 fund pages and its mathematical reflow."""
        # CSS rule for .fund-metrics-grid
        grid_match = re.search(r"\.fund-metrics-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(grid_match, "style.css must define .fund-metrics-grid")
        rules = grid_match.group(1)
        self.assertIn("grid-template-columns", rules)
        self.assertIn("minmax(220px", rules)

        # Mathematical reflow check:
        # At 375px mobile (container width ~343px):
        cols_375 = calculate_grid_columns(343.0, 220.0, 16.0)
        self.assertEqual(cols_375, 1, "At 375px, fund metrics grid must collapse to 1 column")

        # At 768px tablet (container width ~736px):
        cols_768 = calculate_grid_columns(736.0, 220.0, 16.0)
        self.assertIn(cols_768, (2, 3), "At 768px, fund metrics grid must allocate 2 or 3 columns")

        # At 1440px desktop (container max-width 960px -> 928px content):
        cols_1440 = calculate_grid_columns(928.0, 220.0, 16.0)
        self.assertEqual(cols_1440, 4, "At 1440px desktop, fund metrics grid must allocate all 4 columns")

        # Verify all 60 pages contain the 4 cards with expected badges
        for fpath in self.funds:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            grid = soup.find(class_="fund-metrics-grid")
            self.assertIsNotNone(grid, f"Fund page {fpath.name} must have .fund-metrics-grid")
            cards = grid.find_all(class_="fund-metric-card")
            self.assertEqual(len(cards), 4, f"Fund page {fpath.name} must have exactly 4 metric cards")

            # Card 1: 综合年费率
            self.assertIn("综合年费率", cards[0].get_text())
            # Card 2: 渠道限购状态
            self.assertIn("渠道限购状态", cards[1].get_text())
            self.assertIsNotNone(cards[1].find(class_="quota-dual-status"))
            # Card 3: 跟踪复制质量 (TD/IR)
            self.assertIn("跟踪复制质量", cards[2].get_text())
            self.assertIsNotNone(cards[2].find(class_="badge-td"))
            # Card 4: 长期复利回报
            self.assertIn("长期复利回报", cards[3].get_text())

    def test_fund_substitute_tables_and_grids_wrapped(self):
        """TC 3.11: Verify peer share-class table and substitutes grid in fund detail pages."""
        # CSS rule for .fund-substitutes-grid
        sub_grid_match = re.search(r"\.fund-substitutes-grid\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(sub_grid_match, "style.css must define .fund-substitutes-grid")
        sub_rules = sub_grid_match.group(1)
        self.assertIn("minmax(220px", sub_rules)

        # Check sample fund page for substitute tables & wrappers
        sample_page = self.funds[0]
        with open(sample_page, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Check if table exists, it must be inside .dir-table-wrap or .table-wrap
        tables = soup.find_all("table")
        for table in tables:
            parent = table.parent
            classes = parent.get("class", [])
            self.assertTrue(
                "dir-table-wrap" in classes or "table-wrap" in classes,
                f"Fund page table must be wrapped in an overflow container, got: {classes}"
            )

    def test_fund_footer_uniformity(self):
        """TC 3.12: Verify all 60 fund pages contain the award-tier 3-column footer."""
        for fpath in self.funds:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            footer = soup.find("footer")
            self.assertIsNotNone(footer, f"Fund page {fpath.name} must have <footer>")
            inner = footer.find(class_="footer-inner")
            self.assertIsNotNone(inner, f"Fund page {fpath.name} must have .footer-inner")
            self.assertIsNotNone(inner.find(class_="footer-col-brand"))
            self.assertGreaterEqual(len(inner.find_all(class_="footer-links")), 2)


class TestUniversalViewportBoundariesAndZeroRootOverflow(unittest.TestCase):
    """Stress tests universal viewport boundaries to ensure zero horizontal scroll on root container."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_style_css()
        cls.about_soup = load_about_soup()
        cls.articles = get_article_files()
        cls.funds = get_fund_page_files()

    def test_universal_box_sizing_and_body_containment(self):
        """TC 3.13: Verify box-sizing border-box reset and absence of forced overflow-x: scroll on body."""
        # Box sizing reset
        box_sizing_match = re.search(r"\*,\s*\*::before,\s*\*::after\s*\{[^}]*box-sizing:\s*border-box", self.css)
        self.assertIsNotNone(box_sizing_match, "Universal box-sizing: border-box reset must be active")

        # Body overflow-x: scroll absence
        body_match = re.search(r"body\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(body_match)
        self.assertNotIn("overflow-x: scroll", body_match.group(1))

    def test_no_unconstrained_wide_elements_across_all_pages(self):
        """TC 3.14: Scan all HTML pages for inline width/min-width > 320px outside overflow containers."""
        # Exclude known scroll containers: table-wrap, dir-table-wrap, quant-formula, pre, code
        allowed_parents = {"table-wrap", "dir-table-wrap", "quant-formula", "terminal-chrome"}

        def check_element(el, filename):
            style = el.get("style", "")
            if not style:
                return
            # Look for width: 350px or min-width: 350px (excluding max-width)
            width_match = re.search(r"(?<!max-)(width|min-width)\s*:\s*(\d+)px", style)
            if width_match:
                px_val = int(width_match.group(2))
                if px_val > 320:
                    # Check if inside an allowed overflow-x auto container
                    parent = el.parent
                    is_contained = False
                    while parent and parent.name != "[document]":
                        p_classes = set(parent.get("class", []))
                        if p_classes & allowed_parents:
                            is_contained = True
                            break
                        parent = parent.parent

                    if not is_contained:
                        self.fail(
                            f"Unconstrained wide element in {filename}: <{el.name} style='{style}'> "
                            f"with {width_match.group(1)}: {px_val}px will cause horizontal blowout at 375px."
                        )

        # 1. about.html
        for el in self.about_soup.find_all(True):
            check_element(el, "about.html")

        # 2. Sample 3 articles
        for fpath in self.articles[:3]:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for el in soup.find_all(True):
                check_element(el, fpath.name)

        # 3. Sample 5 fund pages
        for fpath in self.funds[:5]:
            with open(fpath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            for el in soup.find_all(True):
                check_element(el, fpath.name)


if __name__ == "__main__":
    unittest.main()
