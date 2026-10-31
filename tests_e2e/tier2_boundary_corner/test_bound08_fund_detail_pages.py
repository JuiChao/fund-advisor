"""Tier 2 Boundary 8: Fund Detail Pages Boundary & Corner Cases Tests."""
import re
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import load_funds_data, FUND_PAGES_DIR


class TestFundDetailPagesBoundary(unittest.TestCase):
    """Verifies edge cases in fund detail pages: single classes, inception dates, star ratings."""

    @classmethod
    def setUpClass(cls):
        cls.funds = load_funds_data()

    def test_single_class_vs_multi_sibling_funds(self):
        """TC 8.1: Verify catalog contains both single-class funds and multi-sibling families."""
        single_class = [f for f in self.funds if len(f.get("siblings", [])) <= 1]
        multi_sibling = [f for f in self.funds if len(f.get("siblings", [])) > 1]
        self.assertGreater(len(single_class), 0, "Catalog must include funds without sibling share classes")
        self.assertGreater(len(multi_sibling), 0, "Catalog must include funds with multiple sibling share classes")

    def test_morningstar_rating_bounds(self):
        """TC 8.2: Verify Morningstar ratings across funds remain between 0 and 5."""
        for f in self.funds:
            star = f.get("morningstar")
            if star is not None:
                self.assertGreaterEqual(star, 0, f"Fund {f['code']} star rating negative")
                self.assertLessEqual(star, 5, f"Fund {f['code']} star rating exceeds 5")

    def test_inception_date_iso_format(self):
        """TC 8.3: Verify all funds have valid ISO-8601 inception dates (YYYY-MM-DD)."""
        for f in self.funds:
            inc_date = f.get("inception_date")
            self.assertIsNotNone(inc_date, f"Fund {f['code']} missing inception_date")
            self.assertRegex(inc_date, r"^\d{4}-\d{2}-\d{2}$",
                             f"Fund {f['code']} inception_date '{inc_date}' must be YYYY-MM-DD")

    def test_tracking_error_percentage_formatting(self):
        """TC 8.4: Verify tracking error formatting in generated HTML includes percentage symbol."""
        sample_page = FUND_PAGES_DIR / f"{self.funds[0]['code']}.html"
        with open(sample_page, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertRegex(content, r"跟踪误差.*?[\d\.]+\s*%", "Tracking error in HTML must be formatted as percentage")

    def test_sibling_code_link_integrity(self):
        """TC 8.5: Verify sibling link targets in fund pages use 6-digit numeric codes."""
        multi_sibling_fund = next(f for f in self.funds if len(f.get("siblings", [])) > 1)
        page_path = FUND_PAGES_DIR / f"{multi_sibling_fund['code']}.html"
        with open(page_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        sibling_links = [a.get("href") for a in soup.find_all("a", href=True) if "/fund/" in a.get("href")]
        for link in sibling_links:
            target_code = link.rstrip("/").split("/")[-1].replace(".html", "")
            self.assertRegex(target_code, r"^\d{6}$", f"Target fund link '{link}' must end in 6-digit code")


if __name__ == "__main__":
    unittest.main()
