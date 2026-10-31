"""Tier 1 Feature 7: Research Reports (18 Articles) Tests."""
import json
import unittest
from bs4 import BeautifulSoup
from tests_e2e.e2e_common import ARTICLES_DIR, get_article_files


class TestResearchReports(unittest.TestCase):
    """Verifies catalog completeness, metadata, schemas, and hub navigation for the 18 research reports."""

    @classmethod
    def setUpClass(cls):
        cls.articles = get_article_files()
        cls.hub_file = ARTICLES_DIR / "index.html"
        with open(cls.hub_file, "r", encoding="utf-8") as f:
            cls.hub_soup = BeautifulSoup(f.read(), "html.parser")

    def test_18_articles_exist(self):
        """TC 7.1: Verify exactly 18 article HTML files exist in public/articles/."""
        self.assertEqual(len(self.articles), 18, f"Must have exactly 18 research articles, found {len(self.articles)}")
        self.assertTrue(self.hub_file.exists(), "public/articles/index.html hub page must exist")

    def test_article_metadata_and_json_ld(self):
        """TC 7.2: Verify title, description, and Article JSON-LD schema in each article."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

            title = soup.find("title")
            self.assertIsNotNone(title, f"Article {path.name} must have a <title>")
            self.assertGreater(len(title.get_text().strip()), 5)

            desc = soup.find("meta", attrs={"name": "description"})
            self.assertIsNotNone(desc, f"Article {path.name} must have a meta description")
            self.assertGreater(len(desc.get("content", "").strip()), 10)

            # Check JSON-LD
            scripts = soup.find_all("script", type="application/ld+json")
            has_article_schema = False
            for s in scripts:
                try:
                    data = json.loads(s.string)
                    if data.get("@type") == "Article":
                        has_article_schema = True
                        break
                except Exception:
                    continue
            self.assertTrue(has_article_schema, f"Article {path.name} must have @type: Article JSON-LD schema")

    def test_article_stylesheet_and_fonts(self):
        """TC 7.3: Verify stylesheet link and font dependencies across all articles."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("style.css", content, f"Article {path.name} must reference style.css")
            self.assertIn("JetBrains+Mono", content, f"Article {path.name} must import JetBrains Mono font")

    def test_hub_links_cover_all_articles(self):
        """TC 7.4: Verify public/articles/index.html links to all 18 articles without broken links."""
        hub_links = [a.get("href") for a in self.hub_soup.find_all("a", href=True)]
        for path in self.articles:
            slug = path.stem
            # Match either slug, slug.html, or /articles/slug
            found = any(slug in link for link in hub_links)
            self.assertTrue(found, f"Hub index.html must link to article '{slug}'")

    def test_article_headings_and_structure(self):
        """TC 7.5: Verify h1 page title and content section presence across all articles."""
        for path in self.articles:
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            h1 = soup.find("h1")
            self.assertIsNotNone(h1, f"Article {path.name} must have an <h1> element")
            self.assertGreater(len(h1.get_text().strip()), 0)
            footer = soup.find("footer")
            self.assertIsNotNone(footer, f"Article {path.name} must contain a <footer>")


if __name__ == "__main__":
    unittest.main()
