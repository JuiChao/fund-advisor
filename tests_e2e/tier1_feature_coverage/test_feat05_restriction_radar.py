"""Tier 1 Feature 5: Market Purchase Restriction Radar Tests."""
import re
import unittest
from tests_e2e.e2e_common import load_index_soup, load_limit_changes_data


class TestRestrictionRadar(unittest.TestCase):
    """Verifies the DOM elements, bulletin drawer, and limit data for the Quota Radar."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.limit_data = load_limit_changes_data()

    def test_radar_and_bulletin_containers(self):
        """TC 5.1: Verify home radar card and quota bulletin container exist."""
        home_radar = self.soup.find(class_="home-quota-radar-card")
        self.assertIsNotNone(home_radar, ".home-quota-radar-card must exist in index.html")

        # Support both container ID and section ID for progressive compatibility
        bulletin_container = self.soup.find(id=re.compile(r"quota-bulletin-(container|section)"))
        self.assertIsNotNone(bulletin_container, "Quota Bulletin container must exist with id quota-bulletin-*")

    def test_alert_ticker_bar_elements(self):
        """TC 5.2: Verify quota alert ticker bar, pulse dot, message, date, and ticker chips."""
        bar = self.soup.find(id="quota-alert-bar")
        self.assertIsNotNone(bar, "#quota-alert-bar must exist")
        self.assertIsNotNone(self.soup.find(id="quota-pulse-dot"), "#quota-pulse-dot must exist")
        self.assertIsNotNone(self.soup.find(id="quota-alert-date"), "#quota-alert-date must exist")
        self.assertIsNotNone(self.soup.find(id="quota-alert-msg"), "#quota-alert-msg must exist")
        self.assertIsNotNone(self.soup.find(id="quota-alert-tickers"), "#quota-alert-tickers container must exist")

    def test_drawer_toggle_and_export_buttons(self):
        """TC 5.3: Verify drawer expand button, drawer body, and social export button."""
        toggle_btn = self.soup.find(id="btn-quota-toggle")
        self.assertIsNotNone(toggle_btn, "#btn-quota-toggle must exist")
        self.assertIsNotNone(self.soup.find(id="quota-toggle-text"), "#quota-toggle-text must exist")

        drawer = self.soup.find(id="quota-board-drawer")
        self.assertIsNotNone(drawer, "#quota-board-drawer must exist")

        export_btn = self.soup.find(id="btn-quota-export-douyin")
        self.assertIsNotNone(export_btn, "#btn-quota-export-douyin must exist")

    def test_quota_statistics_ribbon_and_table(self):
        """TC 5.4: Verify 4 quota KPI statistics ribbon values and comparison table."""
        stats = ["qstat-recent", "qstat-relaxed", "qstat-tightened", "qstat-stable"]
        for stat_id in stats:
            el = self.soup.find(id=stat_id)
            self.assertIsNotNone(el, f"Quota stat element #{stat_id} must exist")

        table = self.soup.find(id="quota-table")
        self.assertIsNotNone(table, "#quota-table must exist")
        tbody = self.soup.find(id="quota-table-tbody")
        self.assertIsNotNone(tbody, "#quota-table-tbody must exist")
        card_list = self.soup.find(id="quota-card-list")
        self.assertIsNotNone(card_list, "#quota-card-list must exist for responsive card stream")

    def test_limit_changes_data_file(self):
        """TC 5.5: Verify public/data/limit_changes.json has valid structure."""
        self.assertIsInstance(self.limit_data, dict, "limit_changes.json must be a JSON object")
        for key in ["last_updated", "total_monitored", "history"]:
            self.assertIn(key, self.limit_data, f"limit_changes.json must contain '{key}'")
        self.assertEqual(self.limit_data["total_monitored"], 60, "total_monitored must equal 60")


if __name__ == "__main__":
    unittest.main()
