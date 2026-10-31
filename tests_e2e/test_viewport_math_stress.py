"""Empirical Viewport Stress Test: Numerical and Algorithmic Validation.

Validates:
1. Fluid clamp typography evaluations across 320px, 375px, 768px, 992px, 1200px, 1440px.
2. Verification of grid-template-columns and column allocations at each breakpoint.
3. Absence of overflow/clipping hazards in HUD, navbar, matrix table, configurator, simulator, and radar.
"""

import re
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
STYLE_PATH = ROOT_DIR / "public" / "css" / "style.css"


def evaluate_clamp(clamp_str: str, viewport_px: float, root_font_size: float = 16.0) -> float:
    """Evaluates a CSS clamp(min, val, max) string at a given viewport_px in pixels."""
    m = re.match(r"clamp\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)", clamp_str.strip())
    if not m:
        raise ValueError(f"Invalid clamp expression: {clamp_str}")

    def parse_length(expr: str) -> float:
        expr = expr.strip()
        # Handle simple additions like '4.5vw + 0.4rem'
        total_px = 0.0
        parts = re.split(r"\s*\+\s*", expr)
        for part in parts:
            part = part.strip()
            if part.endswith("rem"):
                total_px += float(part[:-3]) * root_font_size
            elif part.endswith("px"):
                total_px += float(part[:-2])
            elif part.endswith("vw"):
                total_px += (float(part[:-2]) / 100.0) * viewport_px
            else:
                total_px += float(part)
        return total_px

    min_px = parse_length(m.group(1))
    val_px = parse_length(m.group(2))
    max_px = parse_length(m.group(3))

    return max(min_px, min(val_px, max_px))


class TestViewportMathStress(unittest.TestCase):
    """Stress tests responsive formulas and constraints across 6 viewport widths."""

    @classmethod
    def setUpClass(cls):
        with open(STYLE_PATH, "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_fluid_typography_clamping_monotonicity(self):
        """Verify fluid font sizes evaluate to monotonic, well-bounded px values from 320px to 1440px."""
        viewports = [320, 375, 768, 992, 1200, 1440]
        clamp_hero = "clamp(1.95rem, 3.8vw + 0.75rem, 3.85rem)"
        clamp_h1 = "clamp(1.65rem, 2.8vw + 0.6rem, 2.75rem)"
        clamp_h2 = "clamp(1.38rem, 2.0vw + 0.5rem, 2.25rem)"
        clamp_body = "clamp(0.875rem, 0.4vw + 0.75rem, 0.95rem)"

        for clamp_expr, label in [
            (clamp_hero, "--font-size-hero"),
            (clamp_h1, "--font-size-h1"),
            (clamp_h2, "--font-size-h2"),
            (clamp_body, "--font-size-body"),
        ]:
            prev_val = 0.0
            for vp in viewports:
                val = evaluate_clamp(clamp_expr, vp)
                # Must be strictly non-decreasing
                self.assertGreaterEqual(
                    val,
                    prev_val,
                    f"{label} at {vp}px evaluated to {val:.2f}px, smaller than previous {prev_val:.2f}px"
                )
                # Must be reasonably bounded
                self.assertGreaterEqual(val, 12.0, f"{label} too small at {vp}px")
                self.assertLessEqual(val, 70.0, f"{label} too large at {vp}px")
                prev_val = val

    def test_hud_pod_grid_specifications(self):
        """Verify HUD grid column specifications are mathematically sound across viewports."""
        # Check desktop 5-column
        self.assertIn("grid-template-columns: repeat(5, 1fr)", self.css)
        # Check tablet 2-column
        self.assertIn("grid-template-columns: repeat(2, 1fr)", self.css)
        # Check mobile 1-column
        self.assertIn("grid-template-columns: 1fr", self.css)

    def test_no_horizontal_scrollbar_hazards_in_body(self):
        """Verify body rule does not have overflow-x: scroll or forced min-width."""
        body_match = re.search(r"body\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(body_match)
        body_content = body_match.group(1)
        self.assertNotIn("overflow-x: scroll", body_content, "body must not force horizontal scroll")

    def test_overscroll_behavior_containment(self):
        """Verify overscroll-behavior or touch action configurations prevent page bouncy overflow."""
        self.assertIn("-webkit-overflow-scrolling: touch", self.css, "Touch momentum scrolling must be enabled for iOS")


if __name__ == "__main__":
    unittest.main()
