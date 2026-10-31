"""Tier 1 Feature 2: 60-Target Quantitative Matrix Table Tests."""
import unittest
from tests_e2e.e2e_common import load_index_soup, load_funds_data, load_algo_data


class TestMatrixTable(unittest.TestCase):
    """Verifies the DOM structure, data completeness, and controls for #rank-table."""

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.funds = load_funds_data()
        cls.algo = load_algo_data()

    def test_table_structure_and_sort_headers(self):
        """TC 2.1: Verify #rank-table, thead, tbody, and all 10 sortable data-key headers."""
        table = self.soup.find(id="rank-table")
        self.assertIsNotNone(table, "#rank-table must exist in DOM")
        thead = table.find("thead")
        self.assertIsNotNone(thead, "#rank-table must contain thead")
        tbody = table.find("tbody")
        self.assertIsNotNone(tbody, "#rank-table must contain tbody")

        headers = table.find_all("th")
        header_keys = [th.get("data-key") for th in headers if th.get("data-key")]
        expected_keys = [
            "rank", "name", "fee", "purchase_fee", "tracking_error",
            "scale", "return_3yr", "morningstar", "limit_status", "score"
        ]
        for key in expected_keys:
            self.assertIn(key, header_keys, f"Header with data-key='{key}' must exist on #rank-table")

    def test_60_target_funds_catalog_integrity(self):
        """TC 2.2: Verify exactly 60 funds in data/funds.json with complete required fields."""
        self.assertEqual(len(self.funds), 60, "Target catalog must contain exactly 60 QDII funds")
        required_fields = ["code", "name", "mgmt_fee", "custody_fee", "sales_fee", "index_type", "scale", "tracking_error"]
        for f in self.funds:
            for field in required_fields:
                self.assertIn(field, f, f"Fund {f.get('code', 'UNKNOWN')} missing field {field}")
            self.assertRegex(f["code"], r"^\d{6}$", f"Fund code {f['code']} must be a 6-digit numeric string")
            self.assertIn(f["index_type"], ["纳斯达克100", "标普500"], f"Fund {f['code']} index_type must be Nasdaq 100 or S&P 500")

    def test_filter_controls_and_search_box(self):
        """TC 2.3: Verify index tabs, share class pills, quota filter pills, and search inputs."""
        # Index filter tabs
        rank_filter = self.soup.find(id="rank-filter")
        self.assertIsNotNone(rank_filter, "#rank-filter container must exist")
        index_btns = [btn.get("data-value") for btn in rank_filter.find_all("button")]
        self.assertIn("纳斯达克100", index_btns)
        self.assertIn("标普500", index_btns)
        self.assertIn("ALL", index_btns)

        # Class filter
        class_filter = self.soup.find(id="class-filter")
        self.assertIsNotNone(class_filter, "#class-filter container must exist")
        class_btns = [btn.get("data-value") for btn in class_filter.find_all("button")]
        for c in ["ALL", "A", "C", "OTHER"]:
            self.assertIn(c, class_btns)

        # Quota filter
        quota_filter = self.soup.find(id="quota-filter")
        self.assertIsNotNone(quota_filter, "#quota-filter container must exist")
        quota_btns = [btn.get("data-value") for btn in quota_filter.find_all("button")]
        for q in ["ALL", "BUYABLE", "DIRECT", "PAUSED"]:
            self.assertIn(q, quota_btns)

        # Search box & clear button
        search_input = self.soup.find(id="rank-search")
        self.assertIsNotNone(search_input, "#rank-search input must exist")
        clear_btn = self.soup.find(id="rank-search-clear")
        self.assertIsNotNone(clear_btn, "#rank-search-clear button must exist")

    def test_dual_view_toggle_and_card_stream(self):
        """TC 2.4: Verify table vs card view toggle buttons and responsive card list."""
        toggle = self.soup.find(id="rank-view-toggle")
        self.assertIsNotNone(toggle, "#rank-view-toggle must exist")
        table_btn = self.soup.find(id="view-btn-table")
        card_btn = self.soup.find(id="view-btn-card")
        self.assertIsNotNone(table_btn, "#view-btn-table must exist")
        self.assertIsNotNone(card_btn, "#view-btn-card must exist")
        card_list = self.soup.find(id="rank-card-list")
        self.assertIsNotNone(card_list, "#rank-card-list container must exist for responsive stream")

    def test_quant_scoring_weights_sum_to_one(self):
        """TC 2.5: Verify algorithm.json defines multi-factor scoring weights summing to 100%."""
        weights = self.algo.get("scoring", {}).get("weights", {})
        self.assertTrue(weights, "algorithm.json must define scoring.weights dictionary")
        expected_factors = ["fee", "tracking_error", "scale", "return_3yr", "morningstar", "purchase_fee"]
        total_weight = 0.0
        for factor in expected_factors:
            self.assertIn(factor, weights, f"Scoring model must define weight for factor '{factor}'")
            total_weight += float(weights[factor])
        self.assertAlmostEqual(total_weight, 1.0, places=2, msg="Scoring factor weights must sum to 1.0 (100%)")


if __name__ == "__main__":
    unittest.main()
