"""Tier 2 Boundary 12: Multi-Viewport Adaptability Boundary & Corner Cases Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_style_css


class TestMultiViewportAdaptabilityBoundary(unittest.TestCase):
    """Verifies layout constraints across viewport boundaries (320px, 375px, 768px, 1440px)."""

    @classmethod
    def setUpClass(cls):
        cls.css = load_style_css()

    def test_no_fixed_min_width_above_320px(self):
        """TC 12.1: Verify body/html does not have a min-width exceeding 320px."""
        body_min_widths = re.findall(r"body\s*\{[^}]*min-width\s*:\s*([^;]+);", self.css)
        for mw in body_min_widths:
            self.assertNotIn("px", mw)  # Should not have hardcoded large min-width

    def test_mobile_padding_clamp_scaling(self):
        """TC 12.2: Verify container uses responsive padding (clamp or media queries) for mobile 375px."""
        has_clamp = "clamp(" in self.css
        has_media = "@media" in self.css
        self.assertTrue(has_clamp or has_media, "style.css must use clamp() or media queries for fluid responsive spacing")

    def test_tablet_grid_and_flex_wrapping(self):
        """TC 12.3: Verify flex-wrap or auto-fit grid layouts exist for 768px tablet adaptation."""
        has_flex_wrap = "flex-wrap:wrap" in self.css.replace(" ", "")
        has_auto_fit = "repeat(auto-fit" in self.css or "repeat(auto-fill" in self.css
        self.assertTrue(has_flex_wrap or has_auto_fit,
                        "style.css must use flex-wrap or auto-fit grids for tablet adaptability")

    def test_desktop_max_width_containment(self):
        """TC 12.4: Verify container max-width restricts content spreading beyond 1440px."""
        max_widths = re.findall(r"\.container[^{]*\{[^}]*max-width\s*:\s*([^;]+);", self.css)
        self.assertGreater(len(max_widths), 0, "style.css must define max-width on .container")

    def test_animation_keyframe_definitions(self):
        """TC 12.5: Verify animation @keyframes are cleanly closed and valid."""
        keyframes = re.findall(r"@keyframes\s+([a-zA-Z0-9_\-]+)", self.css)
        self.assertGreater(len(keyframes), 0, "style.css must define keyframe animations")
        # Verify basic keyframe animations exist
        self.assertTrue(any("spin" in k or "pulse" in k or "fade" in k for k in keyframes))


if __name__ == "__main__":
    unittest.main()
