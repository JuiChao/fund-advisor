"""Tier 1 Feature 1: Real-time US Eastern Time Telemetry HUD Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_index_soup, load_style_css, load_app_js


class TestTelemetryHUD(unittest.TestCase):
    """Verifies the DOM structure, CSS styling, and logic contracts of the Telemetry HUD."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.js = load_app_js()

    def test_hud_containers_exist(self):
        """TC 1.1: Verify hero telemetry deck and footer market status containers exist."""
        hero_ticker = self.soup.find(id="hero-quant-ticker")
        self.assertIsNotNone(hero_ticker, "DOM element #hero-quant-ticker must exist in index.html")
        footer_status = self.soup.find(id="footer-us-market-status")
        self.assertIsNotNone(footer_status, "DOM element #footer-us-market-status must exist in index.html")

    def test_market_status_badge_and_classes(self):
        """TC 1.2: Verify market badge, status element, and CSS rules for all 4 market sessions."""
        badge = self.soup.find(id="ticker-market-badge")
        self.assertIsNotNone(badge, "#ticker-market-badge must exist")
        status_span = self.soup.find(id="ticker-market-status")
        self.assertIsNotNone(status_span, "#ticker-market-status must exist inside badge")

        # Verify style.css defines the 4 market session states
        for session_cls in ["market-open", "market-pre", "market-post", "market-closed"]:
            self.assertIn(session_cls, self.css, f"style.css must define rules for .{session_cls}")

    def test_telemetry_kpi_pods_and_sparklines(self):
        """TC 1.3: Verify 3 KPI pods exist with labels, values, and SVG sparkline paths."""
        pods = {
            "tk-pool-count": "标的池监控",
            "tk-avail-count": "可购通道覆盖",
            "tk-min-fee": "最优综合年费"
        }
        for pod_id, expected_label in pods.items():
            pod_el = self.soup.find(id=pod_id)
            self.assertIsNotNone(pod_el, f"Telemetry pod element #{pod_id} must exist")
            parent_box = pod_el.find_parent(class_="ticker-box")
            self.assertIsNotNone(parent_box, f"#{pod_id} must be inside a .ticker-box")
            self.assertIn(expected_label, parent_box.get_text(), f"Pod #{pod_id} must describe {expected_label}")
            svg = parent_box.find("svg", class_="tk-sparkline-svg")
            self.assertIsNotNone(svg, f"Pod #{pod_id} must contain an SVG vector sparkline")
            self.assertIsNotNone(svg.find("path"), f"Pod #{pod_id} SVG must define vector paths")

    def test_latency_gauge_and_pulse_indicators(self):
        """TC 1.4: Verify latency gauge tag and pulse dot elements exist."""
        latency_tag = self.soup.find(id="ticker-latency-tag")
        self.assertIsNotNone(latency_tag, "#ticker-latency-tag must exist in telemetry header")
        pulse_dots = self.soup.find_all(class_="brand-pulse-dot")
        self.assertGreater(len(pulse_dots), 0, "Telemetry and brand headers must include .brand-pulse-dot")
        self.assertIn("LATENCY", latency_tag.get_text(), "Latency tag must display latency metric indicator")

    def test_eastern_time_and_schedule_contract(self):
        """TC 1.5: Verify app.js implements Eastern Time parsing and session window logic."""
        self.assertIn("America/New_York", self.js, "app.js must format time in America/New_York IANA timezone")
        self.assertIn("9:30", self.js, "app.js must check 09:30 ET market open boundary")
        self.assertIn("16:00", self.js, "app.js must check 16:00 ET regular market close boundary")
        # Verify weekend detection
        has_weekend_check = bool(re.search(r"day\s*===?\s*0\s*\|\|\s*day\s*===?\s*6", self.js) or "weekend" in self.js.lower())
        self.assertTrue(has_weekend_check, "app.js must detect weekend days (Saturday=6, Sunday=0)")


if __name__ == "__main__":
    unittest.main()
