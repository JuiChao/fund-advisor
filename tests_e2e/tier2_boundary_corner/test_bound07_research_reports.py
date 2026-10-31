"""Tier 2 Boundary 7: Research Reports Boundary & Corner Cases Tests."""
import json
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import get_article_files


class TestResearchReportsBoundary(unittest.TestCase):
    """Verifies responsive containers, meta tags, schemas, and links across the 18 research articles."""

    @classmethod
    def setUpClass(cls):
        cls.articles = get_article_files()

    def test_meta_robots_indexing_enabled(self):
        """TC 7.1: Verify all 18 articles permit search engine indexing (index, follow)."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            robots = soup.find("meta", attrs={"name": "robots"})
            self.assertIsNotNone(robots, f"Article {path.name} missing robots meta tag")
            content = robots.get("content", "")
            self.assertIn("index", content, f"Article {path.name} robots must permit index")
            self.assertIn("follow", content, f"Article {path.name} robots must permit follow")

    def test_open_graph_social_metadata(self):
        """TC 7.2: Verify Open Graph og:title and og:description tags in articles."""
        for path in self.articles[:6]:  # sample representative batch
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            og_title = soup.find("meta", property="og:title")
            self.assertIsNotNone(og_title, f"Article {path.name} missing og:title")
            og_desc = soup.find("meta", property="og:description")
            self.assertIsNotNone(og_desc, f"Article {path.name} missing og:description")

    def test_json_ld_author_organization(self):
        """TC 7.3: Verify Article schema attributes publisher/author to Fund Advisor."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            scripts = soup.find_all("script", type="application/ld+json")
            found_author = False
            for s in scripts:
                try:
                    data = json.loads(s.string)
                    if data.get("@type") == "Article":
                        author = data.get("author", {})
                        author_name = author.get("name") if isinstance(author, dict) else str(author)
                        if "Fund Advisor" in author_name:
                            found_author = True
                            break
                except Exception:
                    continue
            self.assertTrue(found_author, f"Article {path.name} schema must attribute author to Fund Advisor")

    def test_table_markup_structure_in_articles(self):
        """TC 7.4: Audit tables across articles for valid tabular structure (tr, th/td)."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            tables = soup.find_all("table")
            for t in tables:
                rows = t.find_all("tr")
                self.assertGreater(len(rows), 0, f"Table in {path.name} must have at least one row")
                cells = t.find_all(["th", "td"])
                self.assertGreater(len(cells), 0, f"Table in {path.name} must have cells")

    def test_article_internal_link_targets(self):
        """TC 7.5: Verify internal anchor links in articles point to existing section IDs."""
        sample_path = self.articles[0]
        with open(sample_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        anchor_links = [a.get("href") for a in soup.find_all("a", href=True) if a.get("href").startswith("#")]
        for anchor in anchor_links:
            target_id = anchor[1:]
            if target_id:
                target_el = soup.find(id=target_id)
                self.assertIsNotNone(target_el, f"Anchor {anchor} in {sample_path.name} has missing target element")


if __name__ == "__main__":
    unittest.main()
