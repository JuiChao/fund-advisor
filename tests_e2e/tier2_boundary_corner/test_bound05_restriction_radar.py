"""Tier 2 Boundary 5: Restriction Radar Boundary & Corner Cases Tests."""
import unittest
from tests_e2e.e2e_common import load_funds_data, load_limit_changes_data, load_index_soup


class TestRestrictionRadarBoundary(unittest.TestCase):
    """Verifies quota limit boundaries, channel disparities, and quota sharing detection."""

    @classmethod
    def setUpClass(cls):
        cls.funds = load_funds_data()
        cls.limits = load_limit_changes_data()
        cls.soup = load_index_soup()

    def test_quota_sharing_classification(self):
        """TC 5.1: Verify funds are classified into SHARED vs INDEPENDENT quota sharing."""
        sharing_types = set(f.get("quota_sharing") for f in self.funds if f.get("quota_sharing"))
        self.assertIn("SHARED", sharing_types, "Must detect funds with SHARED A/C quota")
        self.assertIn("INDEPENDENT", sharing_types, "Must detect funds with INDEPENDENT quota")

    def test_daily_limit_boundary_values(self):
        """TC 5.2: Verify daily limits range from paused (0元) to restricted (<=50元 agency, >=100元 direct)."""
        agency_limits = [f.get("daily_limit") for f in self.funds if f.get("daily_limit") is not None]
        direct_limits = [f.get("direct_daily_limit") for f in self.funds if f.get("direct_daily_limit") is not None]
        min_limit = min(agency_limits)
        max_direct = max(direct_limits)
        self.assertEqual(min_limit, 0, f"Expected paused funds with daily_limit=0, found {min_limit}")
        self.assertGreaterEqual(max_direct, 100, f"Expected higher direct sales limits (>=100元), found {max_direct}")

    def test_direct_vs_agency_channel_disparity(self):
        """TC 5.3: Verify detection of funds where official direct limit exceeds agency limit."""
        disparity_funds = [
            f for f in self.funds
            if f.get("direct_daily_limit") and f.get("daily_limit")
            and f["direct_daily_limit"] > f["daily_limit"]
        ]
        self.assertGreater(len(disparity_funds), 0, "Catalog must identify funds where direct sales limit exceeds agency")

    def test_limit_changes_history_data_integrity(self):
        """TC 5.4: Verify total monitored count and date formatting in limit_changes.json."""
        self.assertEqual(self.limits.get("total_monitored"), 60, "Must monitor exactly 60 funds")
        today_date = self.limits.get("today_date")
        self.assertRegex(today_date, r"^\d{4}-\d{2}-\d{2}$", "today_date must follow ISO-8601 (YYYY-MM-DD)")

    def test_default_dom_quota_statistics_fallback(self):
        """TC 5.5: Verify initial markup statistics fallback reflects 60 monitored funds."""
        stable_el = self.soup.find(id="qstat-stable")
        self.assertIsNotNone(stable_el)
        self.assertEqual(stable_el.get_text().strip(), "60", "Default stable fund count in HTML must be 60")


if __name__ == "__main__":
    unittest.main()
