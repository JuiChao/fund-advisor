"""Tier 2 Boundary 11: SEO Pipeline Boundary & Corner Cases Tests."""
import unittest
import xml.etree.ElementTree as ET
from tests_e2e.e2e_common import SITEMAP_XML


class TestSEOPipelineBoundary(unittest.TestCase):
    """Verifies XML namespace compliance, lastmod formats, priorities, and changefreqs."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(SITEMAP_XML)
        cls.root = cls.tree.getroot()
        cls.ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        cls.urls = cls.root.findall("sm:url", cls.ns)

    def test_sitemap_urls_domain_prefix(self):
        """TC 11.1: Verify every URL in sitemap.xml uses production HTTPS domain https://858000.xyz."""
        for u in self.urls:
            loc = u.find("sm:loc", self.ns)
            self.assertIsNotNone(loc, "Each <url> in sitemap must have a <loc>")
            self.assertTrue(loc.text.startswith("https://858000.xyz"),
                            f"URL '{loc.text}' must start with https://858000.xyz")

    def test_iso_8601_lastmod_date_format(self):
        """TC 11.2: Verify lastmod elements conform to ISO-8601 YYYY-MM-DD format."""
        import re
        for u in self.urls:
            lastmod = u.find("sm:lastmod", self.ns)
            if lastmod is not None and lastmod.text:
                self.assertRegex(lastmod.text, r"^\d{4}-\d{2}-\d{2}$",
                                 f"Invalid date format in sitemap: '{lastmod.text}'")

    def test_sitemap_priority_value_bounds(self):
        """TC 11.3: Verify all priority elements are numbers between 0.0 and 1.0."""
        for u in self.urls:
            prio = u.find("sm:priority", self.ns)
            if prio is not None and prio.text:
                val = float(prio.text)
                self.assertGreaterEqual(val, 0.0, f"Priority {val} cannot be negative")
                self.assertLessEqual(val, 1.0, f"Priority {val} cannot exceed 1.0")

    def test_sitemap_changefreq_enum(self):
        """TC 11.4: Verify changefreq elements conform to standard sitemap specification."""
        valid_freqs = {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"}
        for u in self.urls:
            freq = u.find("sm:changefreq", self.ns)
            if freq is not None and freq.text:
                self.assertIn(freq.text, valid_freqs, f"Invalid changefreq value: '{freq.text}'")

    def test_sitemap_no_duplicate_urls(self):
        """TC 11.5: Verify no duplicate URLs exist in sitemap.xml."""
        locs = [u.find("sm:loc", self.ns).text for u in self.urls if u.find("sm:loc", self.ns) is not None]
        self.assertEqual(len(locs), len(set(locs)), "sitemap.xml must not contain duplicate URLs")


if __name__ == "__main__":
    unittest.main()
