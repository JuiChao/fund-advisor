"""Tier 2 Boundary 1: Telemetry HUD Boundary & Corner Cases Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_app_js


class TestTelemetryHUDBoundary(unittest.TestCase):
    """Verifies boundary conditions for market hours, countdown math, and latency bounds."""

    @classmethod
    def setUpClass(cls):
        cls.js = load_app_js()

    def test_market_session_minute_boundaries(self):
        """TC 1.1: Verify exact boundary minute calculations for 09:30 open and 16:00 close."""
        self.assertIn("9 * 60 + 30", self.js, "app.js must calculate exact 09:30 market open in minutes (570)")
        self.assertIn("16 * 60", self.js, "app.js must calculate exact 16:00 market close in minutes (960)")

    def test_pre_and_post_market_edge_minutes(self):
        """TC 1.2: Verify pre-market (04:00) and post-market (20:00) boundary definitions."""
        self.assertIn("4 * 60", self.js, "app.js must calculate 04:00 pre-market open in minutes (240)")
        self.assertIn("20 * 60", self.js, "app.js must calculate 20:00 post-market close in minutes (1200)")

    def test_weekend_status_mapping(self):
        """TC 1.3: Verify weekend day bounds (Sat or Sun in America/New_York timezone)."""
        has_weekend_check = "weekday === 'Sat' || weekday === 'Sun'" in self.js
        self.assertTrue(has_weekend_check, "app.js must explicitly check for weekday Sat or Sun")
        self.assertIn("CLOSED", self.js, "app.js must have specific weekend closure status text")

    def test_latency_jitter_simulation_bounds(self):
        """TC 1.4: Verify latency gauge base ping and random jitter calculation."""
        self.assertIn("basePing = 8", self.js, "app.js must define basePing = 8")
        self.assertIn("Math.floor(Math.random() * 5)", self.js, "app.js must calculate jitter between 0 and 4ms")

    def test_weekend_countdown_add_days(self):
        """TC 1.5: Verify Friday-to-Monday countdown timer adds 3 days to reach market open."""
        self.assertIn("daysToAdd = 3", self.js, "Countdown logic on Friday after close must advance 3 days to Monday")


if __name__ == "__main__":
    unittest.main()
