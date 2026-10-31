"""Tier 1 Feature 12: Responsive Multi-Viewport Adaptability Tests."""
import re
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import (
    load_index_soup, load_about_soup, load_style_css,
    get_article_files, get_fund_page_files
)


class TestMultiViewportAdaptability(unittest.TestCase):
    """Verifies responsive viewport configurations, media queries, table wrappers, and drawer controls."""

    @classmethod
    def setUpClass(cls):
        cls.index_soup = load_index_soup()
        cls.about_soup = load_about_soup()
        cls.css = load_style_css()
        cls.articles = get_article_files()
        cls.funds = get_fund_page_files()

    def test_viewport_meta_tags_across_pages(self):
        """TC 12.1: Verify viewport meta tag exists with width=device-width on all page archetypes."""
        pages_to_check = [
            ("index.html", self.index_soup),
            ("about.html", self.about_soup)
        ]
        # Add sample article and sample fund page
        with open(self.articles[0], "r", encoding="utf-8") as f:
            pages_to_check.append((self.articles[0].name, BeautifulSoup(f.read(), "html.parser")))
        with open(self.funds[0], "r", encoding="utf-8") as f:
            pages_to_check.append((self.funds[0].name, BeautifulSoup(f.read(), "html.parser")))

        for name, soup in pages_to_check:
            meta = soup.find("meta", attrs={"name": "viewport"})
            self.assertIsNotNone(meta, f"Page {name} must have viewport meta tag")
            content = meta.get("content", "")
            self.assertIn("width=device-width", content, f"Page {name} viewport must set width=device-width")

    def test_responsive_media_queries_in_css(self):
        """TC 12.2: Verify style.css defines standard mobile and tablet responsive media queries."""
        self.assertRegex(self.css, r"@media\s*\([^\)]*max-width\s*:\s*(768px|48rem)",
                         "style.css must define mobile breakpoint media query (768px)")
        self.assertRegex(self.css, r"@media\s*\([^\)]*max-width\s*:\s*(1024px|64rem)",
                         "style.css must define tablet breakpoint media query (1024px)")

    def test_table_overflow_scroll_wrappers(self):
        """TC 12.3: Verify .table-wrap classes have overflow-x auto styling in style.css."""
        self.assertIn(".table-wrap", self.css, "style.css must define .table-wrap")
        table_wrap_rules = re.findall(r"\.table-wrap[^{]*\{([^}]+)\}", self.css)
        has_overflow_x = any("overflow-x" in r for r in table_wrap_rules)
        self.assertTrue(has_overflow_x, ".table-wrap must configure overflow-x for horizontal scrolling on mobile")

    def test_mobile_nav_drawer_and_card_list(self):
        """TC 12.4: Verify mobile drawer toggle (.nav-toggle) and mobile card stream (#rank-card-list)."""
        nav_toggle = self.index_soup.find(class_="nav-toggle")
        self.assertIsNotNone(nav_toggle, ".nav-toggle hamburger button must exist on navbar")
        nav_links = self.index_soup.find(id="nav-links")
        self.assertIsNotNone(nav_links, "#nav-links drawer list must exist")

        card_list = self.index_soup.find(id="rank-card-list")
        self.assertIsNotNone(card_list, "#rank-card-list must exist for mobile card stream")

    def test_universal_box_sizing(self):
        """TC 12.5: Verify universal box-sizing border-box reset exists to prevent viewport blowout."""
        has_box_sizing = bool(re.search(r"box-sizing\s*:\s*border-box", self.css))
        self.assertTrue(has_box_sizing, "style.css must define box-sizing: border-box")


if __name__ == "__main__":
    unittest.main()
