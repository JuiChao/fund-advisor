"""Tier 1 Feature 11: SEO Generation Pipeline Tests."""
import unittest
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import (
    SCRAPER_SEO_PY, SITEMAP_XML, ROBOTS_TXT,
    get_article_files, get_fund_page_files
)


class TestSEOPipeline(unittest.TestCase):
    """Verifies the SEO generator script, sitemap.xml, robots.txt, and canonical URLs."""

    @classmethod
    def setUpClass(cls):
        cls.articles = get_article_files()
        cls.fund_pages = get_fund_page_files()

    def test_generator_script_exists_and_structured(self):
        """TC 11.1: Verify scraper/generate_seo.py exists and defines HTML_TEMPLATE and sitemap logic."""
        self.assertTrue(SCRAPER_SEO_PY.exists(), "scraper/generate_seo.py must exist")
        with open(SCRAPER_SEO_PY, "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn("HTML_TEMPLATE", code, "generate_seo.py must define HTML_TEMPLATE")
        self.assertIn("SITEMAP_FILE", code, "generate_seo.py must define SITEMAP_FILE generation")

    def test_sitemap_xml_validity(self):
        """TC 11.2: Verify public/sitemap.xml is valid XML with urlset namespace."""
        self.assertTrue(SITEMAP_XML.exists(), "public/sitemap.xml must exist")
        tree = ET.parse(SITEMAP_XML)
        root = tree.getroot()
        self.assertIn("urlset", root.tag, "Sitemap root element must be urlset")

    def test_sitemap_url_coverage(self):
        """TC 11.3: Verify sitemap covers homepage, about, 18 articles, and 60 fund pages (>= 80 URLs)."""
        tree = ET.parse(SITEMAP_XML)
        root = tree.getroot()
        urls = [loc.text for loc in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertGreaterEqual(len(urls), 80, f"Sitemap should contain >= 80 URLs, found {len(urls)}")

        # Verify all articles are represented in sitemap
        for a in self.articles:
            expected_slug = a.stem
            found = any(expected_slug in u for u in urls)
            self.assertTrue(found, f"Article {expected_slug} must be listed in sitemap.xml")

        # Verify all fund pages are represented in sitemap
        for fp in self.fund_pages:
            code = fp.stem
            found = any(f"/fund/{code}" in u for u in urls)
            self.assertTrue(found, f"Fund page {code} must be listed in sitemap.xml")

    def test_robots_txt_and_sitemap_declaration(self):
        """TC 11.4: Verify public/robots.txt allows indexing and references sitemap.xml."""
        self.assertTrue(ROBOTS_TXT.exists(), "public/robots.txt must exist")
        with open(ROBOTS_TXT, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("User-agent: *", content, "robots.txt must declare User-agent: *")
        self.assertIn("Allow: /", content, "robots.txt must allow root crawling")
        self.assertIn("sitemap.xml", content, "robots.txt must link to sitemap.xml")

    def test_canonical_urls_in_fund_pages(self):
        """TC 11.5: Verify canonical links in fund pages match standard URL convention."""
        sample_page = self.fund_pages[0]
        with open(sample_page, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        canonical = soup.find("link", rel="canonical")
        self.assertIsNotNone(canonical, f"{sample_page.name} must have a canonical link")
        expected_url = f"https://858000.xyz/fund/{sample_page.stem}"
        self.assertEqual(canonical.get("href"), expected_url, "Canonical URL must match fund detail URL")


if __name__ == "__main__":
    unittest.main()
