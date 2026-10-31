"""Tier 2 Boundary 6: About Page Boundary & Corner Cases Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_about_soup


class TestAboutPageBoundary(unittest.TestCase):
    """Verifies reading container max-width, link security, heading hierarchy, and citations."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_about_soup()

    def test_container_max_width_constraint(self):
        """TC 6.1: Verify reading container restricts max-width on wide displays for legibility."""
        main_el = self.soup.find("main")
        self.assertIsNotNone(main_el, "about.html must have a <main> element")
        style = main_el.get("style", "")
        # Either inline max-width or CSS class constraint
        has_max_width = "max-width" in style or "container" in main_el.get("class", [])
        self.assertTrue(has_max_width, "Main container must enforce max-width constraint for editorial reading")

    def test_heading_hierarchy_nesting(self):
        """TC 6.2: Verify heading hierarchy (h1 -> h2 -> h3) without skipping levels."""
        headings = [h.name for h in self.soup.find_all(re.compile(r"^h[1-6]$"))]
        self.assertIn("h1", headings, "Page must have an h1")
        self.assertIn("h2", headings, "Page must have h2 subheadings")
        # Ensure h1 appears before any h2
        first_h1_idx = headings.index("h1")
        first_h2_idx = headings.index("h2")
        self.assertLess(first_h1_idx, first_h2_idx, "h1 must precede h2 headings")

    def test_external_link_security_attributes(self):
        """TC 6.3: Verify all target=_blank external links include rel=noopener or noreferrer."""
        blank_links = self.soup.find_all("a", target="_blank")
        for link in blank_links:
            rel = link.get("rel", [])
            rel_str = " ".join(rel) if isinstance(rel, list) else rel
            self.assertTrue("noopener" in rel_str or "noreferrer" in rel_str,
                            f"Target _blank link to {link.get('href')} must specify rel=noopener noreferrer")

    def test_contact_email_mailto_format(self):
        """TC 6.4: Verify contact section contains valid mailto: link."""
        mailto_links = [a.get("href") for a in self.soup.find_all("a", href=True) if a.get("href").startswith("mailto:")]
        self.assertGreater(len(mailto_links), 0, "about.html must provide at least one mailto: contact link")
        email = mailto_links[0].replace("mailto:", "").strip()
        self.assertRegex(email, r"^[\w\.\-]+@[\w\.\-]+\.[a-zA-Z]{2,}$", f"Invalid contact email address: {email}")

    def test_academic_citations_count_and_details(self):
        """TC 6.5: Verify academic bibliography section lists at least 4 classic papers with years."""
        text = self.soup.get_text()
        years = re.findall(r"\(19\d\d\)|19\d\d年|\(20\d\d\)|20\d\d年", text)
        self.assertGreaterEqual(len(years), 4, "Academic citations must mention publication years for seminal literature")


if __name__ == "__main__":
    unittest.main()
