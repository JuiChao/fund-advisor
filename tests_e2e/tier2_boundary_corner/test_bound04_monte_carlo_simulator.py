"""Tier 2 Boundary 4: Monte Carlo Simulator Boundary & Corner Cases Tests."""
import json
import unittest
from tests_e2e.e2e_common import SIMULATIONS_JSON, SIM_WORKER_JS


class TestMonteCarloSimulatorBoundary(unittest.TestCase):
    """Verifies simulation boundaries, Box-Muller transforms, and percentile monotonicity."""

    @classmethod
    def setUpClass(cls):
        with open(SIMULATIONS_JSON, "r", encoding="utf-8") as f:
            cls.sim_data = json.load(f)
        with open(SIM_WORKER_JS, "r", encoding="utf-8") as f:
            cls.worker_code = f.read()

    def test_horizon_years_coverage_and_bounds(self):
        """TC 4.1: Verify horizon years range starts at 5 and ends at 30 (26 discrete steps)."""
        years = self.sim_data.get("years_range", [])
        self.assertEqual(len(years), 26, "Must contain exactly 26 years (5 to 30)")
        self.assertEqual(years[0], 5, "Lower horizon bound must be 5 years")
        self.assertEqual(years[-1], 30, "Upper horizon bound must be 30 years")

    def test_n_simulations_scale(self):
        """TC 4.2: Verify precomputed dataset runs exactly 5,000 Monte Carlo paths."""
        self.assertEqual(self.sim_data.get("n_simulations"), 5000, "Must be computed with 5,000 paths")

    def test_box_muller_transform_in_worker(self):
        """TC 4.3: Verify Box-Muller Gaussian random variable generator in sim-worker.js."""
        # Check Box-Muller math: Math.sqrt(-2 * Math.log(...)) and Math.cos(2 * Math.PI * ...)
        has_log = "Math.log" in self.worker_code
        has_sqrt = "Math.sqrt" in self.worker_code
        has_trig = "Math.cos" in self.worker_code or "Math.sin" in self.worker_code
        self.assertTrue(has_log and has_sqrt and has_trig,
                        "sim-worker.js must implement Box-Muller transform for pseudo-random normals")

    def test_percentile_ladder_monotonic_ordering(self):
        """TC 4.4: Verify strict percentile monotonicity: p5 <= p25 <= median <= p75 <= p95."""
        strategies = self.sim_data.get("strategies", [])
        for strat in strategies:
            by_years = strat.get("ideal", {}).get("by_years", {})
            for yr, metrics in by_years.items():
                p5 = metrics["p5"]
                p25 = metrics["p25"]
                median = metrics["median"]
                p75 = metrics["p75"]
                p95 = metrics["p95"]
                self.assertLessEqual(p5, p25, f"Strat {strat['key']} Yr {yr}: p5 ({p5}) > p25 ({p25})")
                self.assertLessEqual(p25, median, f"Strat {strat['key']} Yr {yr}: p25 ({p25}) > median ({median})")
                self.assertLessEqual(median, p75, f"Strat {strat['key']} Yr {yr}: median ({median}) > p75 ({p75})")
                self.assertLessEqual(p75, p95, f"Strat {strat['key']} Yr {yr}: p75 ({p75}) > p95 ({p95})")

    def test_long_term_compound_growth_boundary(self):
        """TC 4.5: Verify compound terminal wealth at year 30 strictly exceeds year 5."""
        for strat in self.sim_data.get("strategies", []):
            by_years = strat.get("ideal", {}).get("by_years", {})
            wealth_5 = by_years["5"]["median"]
            wealth_30 = by_years["30"]["median"]
            self.assertGreater(wealth_30, wealth_5 * 4,
                               f"Strat {strat['key']}: 30-year wealth ({wealth_30}) should far exceed 5-year ({wealth_5})")


if __name__ == "__main__":
    unittest.main()
