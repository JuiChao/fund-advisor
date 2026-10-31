"""Tier 1 Feature 8: 60 Individual Fund Detail Pages Tests."""
import json
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import load_funds_data, FUND_PAGES_DIR, get_fund_page_files


class TestFundDetailPages(unittest.TestCase):
    """Verifies coverage, metadata, financial schemas, and metrics across all 60 fund pages."""

    @classmethod
    def setUpClass(cls):
        cls.funds = load_funds_data()
        cls.fund_files = get_fund_page_files()

    def test_60_fund_pages_exist(self):
        """TC 8.1: Verify each of the 60 fund codes has a generated HTML page in public/fund/."""
        self.assertEqual(len(self.fund_files), 60, f"Expected 60 fund pages, found {len(self.fund_files)}")
        for f in self.funds:
            code = f["code"]
            page_path = FUND_PAGES_DIR / f"{code}.html"
            self.assertTrue(page_path.exists(), f"Fund detail page {code}.html must exist")

    def test_fund_page_metadata_and_financial_schema(self):
        """TC 8.2: Verify title, description, and FinancialProduct JSON-LD schema."""
        for path in self.fund_files:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            title = soup.find("title")
            self.assertIsNotNone(title, f"{path.name} must have a title")
            self.assertIn(path.stem, title.get_text(), f"{path.name} title must contain fund code")

            desc = soup.find("meta", attrs={"name": "description"})
            self.assertIsNotNone(desc, f"{path.name} must have a meta description")

            # Check JSON-LD
            scripts = soup.find_all("script", type="application/ld+json")
            has_product_schema = False
            for s in scripts:
                try:
                    data = json.loads(s.string)
                    schema_type = data.get("@type")
                    if schema_type in ["FinancialProduct", "Product"]:
                        has_product_schema = True
                        break
                except Exception:
                    continue
            self.assertTrue(has_product_schema, f"{path.name} must define FinancialProduct/Product schema")

    def test_quantitative_metrics_in_pages(self):
        """TC 8.3: Verify quantitative metrics (fees, scale, tracking error) are displayed."""
        # Sample a subset of funds across different categories
        sample_codes = [self.funds[0]["code"], self.funds[15]["code"], self.funds[30]["code"], self.funds[-1]["code"]]
        for code in sample_codes:
            page_path = FUND_PAGES_DIR / f"{code}.html"
            with open(page_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue("管理费" in content or "费率" in content, f"{code}.html must mention fee metrics")
            self.assertTrue("跟踪误差" in content or "规模" in content, f"{code}.html must display tracking error or scale")

    def test_navigation_and_breadcrumb_back_links(self):
        """TC 8.4: Verify navigation links back to the home / ranking page."""
        for path in self.fund_files[:10]:  # sample 10 pages
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            has_home_link = any(l in ["/", "/#ranking", "#ranking", "index.html"] or "858000.xyz" in l for l in links)
            self.assertTrue(has_home_link, f"{path.name} must include link back to home or ranking")

    def test_quota_channel_and_sibling_disclosure(self):
        """TC 8.5: Verify quota status or channel limit disclosure on fund pages."""
        for path in self.fund_files[:10]:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            has_channel_info = "直销" in content or "代销" in content or "限购" in content or "申购" in content
            self.assertTrue(has_channel_info, f"{path.name} must disclose purchase limit or channel information")


if __name__ == "__main__":
    unittest.main()
