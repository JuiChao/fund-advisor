"""Tier 1 Feature 6: About Page Presentation Tests."""
import json
import unittest
from tests_e2e.e2e_common import load_about_soup, ABOUT_HTML


class TestAboutPage(unittest.TestCase):
    """Verifies the layout, structured data, and content sections of about.html."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_about_soup()

    def test_html_document_standards(self):
        """TC 6.1: Verify valid HTML5 document standards, lang, charset, viewport, and title."""
        self.assertTrue(ABOUT_HTML.exists(), "public/about.html must exist")
        html_el = self.soup.find("html")
        self.assertEqual(html_el.get("lang"), "zh-CN", "html lang must be zh-CN")
        charset = self.soup.find("meta", charset=True)
        self.assertEqual(charset.get("charset").upper(), "UTF-8", "charset must be UTF-8")
        viewport = self.soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(viewport, "viewport meta tag must exist")
        self.assertIn("width=device-width", viewport.get("content", ""))
        self.assertIsNotNone(self.soup.find("title"), "Page must have a <title>")

    def test_schema_org_structured_data(self):
        """TC 6.2: Verify schema.org AboutPage structured JSON-LD."""
        scripts = self.soup.find_all("script", type="application/ld+json")
        self.assertGreater(len(scripts), 0, "about.html must contain JSON-LD structured data")
        found_about_schema = False
        for s in scripts:
            try:
                data = json.loads(s.string)
                if data.get("@type") == "AboutPage":
                    found_about_schema = True
                    self.assertEqual(data.get("@context"), "https://schema.org")
                    self.assertIn("Fund Advisor", data.get("name", ""))
            except Exception:
                continue
        self.assertTrue(found_about_schema, "about.html must contain valid @type: AboutPage schema")

    def test_9_core_methodology_sections(self):
        """TC 6.3: Verify presence of all 9 core methodology section headings."""
        h2_headings = [h2.get_text().strip() for h2 in self.soup.find_all("h2")]
        expected_keywords = [
            "平台使命与创立初衷",
            "核心量化模型与算法体系",
            "量化投研团队与专业资质背景",
            "学术理论文献与量化模型引用清单",
            "数据流水线与更新机制",
            "内容审校与质量控制流程",
            "独立性与无利益冲突声明",
            "法律合规与免责声明",
            "团队联系与技术支持"
        ]
        for kw in expected_keywords:
            matched = any(kw in h for h in h2_headings)
            self.assertTrue(matched, f"about.html must contain section h2 containing '{kw}'")

    def test_navigation_and_active_state(self):
        """TC 6.4: Verify navbar brand, navigation links, and active class on '关于我们'."""
        navbar = self.soup.find("nav", class_="navbar")
        self.assertIsNotNone(navbar, "about.html must contain .navbar")
        links_container = navbar.find(id="nav-links")
        self.assertIsNotNone(links_container, "navbar must contain #nav-links")

        about_link = links_container.find("a", href="/about") or links_container.find("a", href="about.html")
        self.assertIsNotNone(about_link, "Nav links must include about link")
        classes = about_link.get("class", [])
        self.assertIn("on", classes, "About link must have 'on' active class in about.html")
        self.assertIsNotNone(navbar.find(id="theme-toggle"), "Navbar must include theme toggle button")

    def test_academic_bibliography_citations(self):
        """TC 6.5: Verify academic literature citations in methodology section."""
        content = self.soup.get_text()
        seminal_authors = ["Markowitz", "Sharpe", "Sortino"]
        for author in seminal_authors:
            self.assertIn(author, content, f"Academic methodology must cite seminal research by {author}")


if __name__ == "__main__":
    unittest.main()
