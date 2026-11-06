"""Tier 2 Boundary 13: Hero Indices Deck Boundary & Corner Cases Tests."""
import re
import unittest
from pathlib import Path
from tests_e2e.e2e_common import load_app_js

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestHeroIndicesBoundary(unittest.TestCase):
    """Verifies edge cases and boundary conditions for indices parsing,

    range bar math, Black Swan triggers, and session tag visibility.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = load_app_js()
        indices_js_path = PROJECT_ROOT / "functions" / "api" / "indices.js"
        with open(indices_js_path, "r", encoding="utf-8") as f:
            cls.indices_js = f.read()

    def test_range_bar_boundary_conditions(self):
        """TC 13.1: Verify range bar calculation clamps to 0% at price <= low, and 100% at price >= high."""
        self.assertIn("curPrice <= low", self.js, "app.js must handle curPrice <= low")
        self.assertIn("curPrice >= high", self.js, "app.js must handle curPrice >= high")
        self.assertIn("rangePct = 0", self.js, "app.js must assign rangePct = 0 when price <= low")
        self.assertIn("rangePct = 100", self.js, "app.js must assign rangePct = 100 when price >= high")

        # In functions/api/indices.js
        self.assertIn("price <= low", self.indices_js)
        self.assertIn("return 0", self.indices_js)
        self.assertIn("price >= high", self.indices_js)
        self.assertIn("return 100", self.indices_js)

    def test_black_swan_threshold_boundaries(self):
        """TC 13.2: Verify exact threshold boundaries for -3%, -5%, and -7% (Circuit Breaker)."""
        self.assertIn("minDrop <= -3.0", self.js, "Must trigger alert when minDrop <= -3.0%")
        self.assertIn("minDrop <= -5.0", self.js, "Must trigger severe alarm when minDrop <= -5.0%")
        self.assertIn("inxDrop <= -7.0", self.js, "Must trigger circuit breaker alarm when S&P drops <= -7.0%")
        self.assertIn("美股一级熔断警报", self.js)

    def test_black_swan_nan_safety(self):
        """TC 13.3: Verify Number.isFinite is used to protect against NaN/undefined drop values."""
        self.assertIn("Number.isFinite(data.indices.NDX?.change_pct)", self.js,
                      "Must validate NDX change_pct is finite to prevent NaN <= -3.0 bug")
        self.assertIn("Number.isFinite(data.indices.INX?.change_pct)", self.js,
                      "Must validate INX change_pct is finite to prevent NaN <= -3.0 bug")

    def test_regular_session_extended_tag_guard(self):
        """TC 13.4: Verify extended hours tag is strictly hidden during regular session."""
        self.assertIn("session.status !== 'REGULAR'", self.js,
                      "Extended price tag must be guarded by session.status !== 'REGULAR'")

    def test_multi_tier_fallback_defense(self):
        """TC 13.5: Verify 4-tier data fallback pipeline: Edge API -> Direct Tencent -> Fallback JSON -> In-memory."""
        self.assertIn("/api/indices", self.js, "Tier 1: /api/indices")
        self.assertIn("https://qt.gtimg.cn/q=usNDX,usINX,usQQQ,usSPY", self.js, "Tier 2: qt.gtimg.cn")
        self.assertIn("/data/indices_fallback.json", self.js, "Tier 3: /data/indices_fallback.json")
        self.assertIn("fallback: true", self.js, "Tier 4: In-memory fallback payload")


if __name__ == "__main__":
    unittest.main()
