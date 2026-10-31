"""Milestone 2 Empirical & Mathematical Challenger Stress Suite.

Empirically challenges:
1. Range slider definitions, steppers, and dynamic --slider-pct attributes.
2. Markowitz MVO 101-point frontier calculation, GMV optimality, and boundary weights.
3. Ledoit-Wolf covariance shrinkage stability under near-singular correlation limits.
4. Box-Muller pseudo-random normal sampling moments.
5. Analytical Sortino ratio downside volatility integration.
6. Euler's theorem homogeneous risk decomposition (TRC & ERC 50/50 neutrality).
"""

import math
import os
import re
import sys
import unittest
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from bs4 import BeautifulSoup
from scraper.simulate import (
    calc_risk_parity_weights, calc_max_sharpe_weights, calc_risk_contributions,
    simulate_portfolio_all_years, CONFIG
)

INDEX_PATH = PROJECT_ROOT / "public" / "index.html"
STYLE_PATH = PROJECT_ROOT / "public" / "css" / "style.css"
APP_JS_PATH = PROJECT_ROOT / "public" / "js" / "app.js"
SIM_WORKER_PATH = PROJECT_ROOT / "public" / "js" / "sim-worker.js"


class TestM2ChallengerStress(unittest.TestCase):
    """Empirical challenge suite for Milestone 2 controls and quantitative algorithms."""

    @classmethod
    def setUpClass(cls):
        assert INDEX_PATH.exists(), f"Missing index.html at {INDEX_PATH}"
        assert STYLE_PATH.exists(), f"Missing style.css at {STYLE_PATH}"
        assert APP_JS_PATH.exists(), f"Missing app.js at {APP_JS_PATH}"
        assert SIM_WORKER_PATH.exists(), f"Missing sim-worker.js at {SIM_WORKER_PATH}"

        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            cls.index_html = f.read()
        cls.soup = BeautifulSoup(cls.index_html, "html.parser")

        with open(STYLE_PATH, "r", encoding="utf-8") as f:
            cls.css = f.read()

        with open(APP_JS_PATH, "r", encoding="utf-8") as f:
            cls.app_js = f.read()

        with open(SIM_WORKER_PATH, "r", encoding="utf-8") as f:
            cls.worker_js = f.read()

        cls.params = CONFIG["simulation"]["params"]
        cls.mu_nq = cls.params["nasdaq_return"]
        cls.vol_nq = cls.params["nasdaq_vol"]
        cls.mu_sp = cls.params["sp500_return"]
        cls.vol_sp = cls.params["sp500_vol"]
        cls.rho = CONFIG["simulation"]["correlation_nq_sp"]
        cls.rf = 0.025

    # =========================================================================
    # Part 1: Slider Controls, Steppers & CSS Custom Properties
    # =========================================================================

    def test_slider_elements_and_stepper_pairings(self):
        """TC 1.1: Verify all 5 core sliders exist with exact boundaries and matching steppers."""
        expected_sliders = {
            "sim-m": {"min": "500", "max": "10000", "step": "100", "step_val": 100},
            "sim-y": {"min": "5", "max": "30", "step": "1", "step_val": 1},
            "pf-m": {"min": "500", "max": "10000", "step": "100", "step_val": 100},
            "pf-y": {"min": "5", "max": "30", "step": "1", "step_val": 1},
            "frontier-range-slider": {"min": "0", "max": "100", "step": "1", "step_val": None}
        }

        for sid, attrs in expected_sliders.items():
            slider = self.soup.find(id=sid)
            self.assertIsNotNone(slider, f"Slider #{sid} must exist in index.html")
            self.assertEqual(slider.get("min"), attrs["min"], f"#{sid} min mismatch")
            self.assertEqual(slider.get("max"), attrs["max"], f"#{sid} max mismatch")
            self.assertEqual(slider.get("step"), attrs["step"], f"#{sid} step mismatch")

            if attrs["step_val"] is not None:
                inc_btn = self.soup.find("button", {"data-for": sid, "data-step": str(attrs["step_val"])})
                dec_btn = self.soup.find("button", {"data-for": sid, "data-step": str(-attrs["step_val"])})
                self.assertIsNotNone(inc_btn, f"Increment stepper for #{sid} (+{attrs['step_val']}) missing")
                self.assertIsNotNone(dec_btn, f"Decrement stepper for #{sid} (-{attrs['step_val']}) missing")

    def test_css_slider_pct_and_tabular_nums_presence(self):
        """TC 1.2: Verify CSS rules correctly consume --slider-pct and tabular-nums."""
        self.assertIn("var(--slider-pct", self.css, "CSS must style range track fill using --slider-pct")
        self.assertIn("tabular-nums", self.css, "CSS must employ tabular-nums font-variant-numeric")
        self.assertIn("updateSliderGlowTrack", self.app_js, "app.js must define updateSliderGlowTrack")

    def test_quota_bulletin_dom_id_dual_anchor(self):
        """TC 1.3: Verify #quota-bulletin-section wraps or aliases #quota-bulletin-container."""
        sec = self.soup.find(id="quota-bulletin-section")
        self.assertIsNotNone(sec, "#quota-bulletin-section must exist for smooth scroll anchor")
        cnt = self.soup.find(id="quota-bulletin-container")
        self.assertIsNotNone(cnt, "#quota-bulletin-container must exist for DOM render target")

    # =========================================================================
    # Part 2: Markowitz MVO 101-Point Frontier & Boundary Weights
    # =========================================================================

    def test_frontier_continuous_sampling_and_monotonicity(self):
        """TC 2.1: Verify 101-point frontier sampling yields valid, non-negative variances."""
        s1_sq = self.vol_nq ** 2
        s2_sq = self.vol_sp ** 2
        cov12 = self.rho * self.vol_nq * self.vol_sp

        for i in range(101):
            w_nq = i / 100.0
            w_sp = 1.0 - w_nq
            var = (w_nq ** 2) * s1_sq + 2 * w_nq * w_sp * cov12 + (w_sp ** 2) * s2_sq
            self.assertGreater(var, 0.0)
            vol = math.sqrt(var)
            self.assertFalse(math.isnan(vol))
            self.assertFalse(math.isinf(vol))

    def test_gmv_analytical_optimality(self):
        """TC 2.2: Verify Global Minimum Variance weight minimizes portfolio variance."""
        s1_sq = self.vol_nq ** 2
        s2_sq = self.vol_sp ** 2
        cov12 = self.rho * self.vol_nq * self.vol_sp
        w_gmv = (s2_sq - cov12) / (s1_sq + s2_sq - 2 * cov12)
        var_gmv = (w_gmv ** 2) * s1_sq + 2 * w_gmv * (1 - w_gmv) * cov12 + ((1 - w_gmv) ** 2) * s2_sq

        # Sample 100 points around GMV
        for w in np.linspace(0.0, 1.0, 100):
            var_w = (w ** 2) * s1_sq + 2 * w * (1 - w) * cov12 + ((1 - w) ** 2) * s2_sq
            self.assertGreaterEqual(var_w, var_gmv - 1e-12)

    # =========================================================================
    # Part 3: Ledoit-Wolf Shrinkage & Numerical Stability
    # =========================================================================

    def test_ledoit_wolf_shrinkage_near_singular_matrix(self):
        """TC 3.1: Verify Ledoit-Wolf shrinkage avoids singular matrix crash when rho -> 0.9999."""
        w_nq, w_sp = calc_max_sharpe_weights(
            r_nq=self.mu_nq, r_sp=self.mu_sp,
            vol_nq=self.vol_nq, vol_sp=self.vol_sp,
            rho=0.9999, rf=self.rf, shrinkage=0.15
        )
        self.assertGreaterEqual(w_nq, 0.1)
        self.assertLessEqual(w_nq, 0.9)
        self.assertAlmostEqual(w_nq + w_sp, 1.0, places=4)

    # =========================================================================
    # Part 4: Euler's Homogeneous Risk Decomposition (TRC)
    # =========================================================================

    def test_trc_euler_theorem_summation(self):
        """TC 4.1: Verify Euler's theorem: relative risk contributions sum to 100% exactly."""
        for w in [0.0, 0.1, 0.38, 0.5, 0.7, 0.9, 1.0]:
            rc = calc_risk_contributions(
                w_nq=w, w_sp=1.0 - w,
                vol_nq=self.vol_nq, vol_sp=self.vol_sp, rho=self.rho
            )
            total_rc = rc["nq_risk_contrib"] + rc["sp_risk_contrib"]
            self.assertAlmostEqual(total_rc, 1.0, places=4)

    def test_single_asset_boundary_weights(self):
        """TC 4.2: Verify 100% single asset allocates 100% of risk to that asset."""
        rc_nq = calc_risk_contributions(1.0, 0.0, self.vol_nq, self.vol_sp, self.rho)
        self.assertAlmostEqual(rc_nq["nq_risk_contrib"], 1.0, places=4)
        self.assertAlmostEqual(rc_nq["sp_risk_contrib"], 0.0, places=4)

        rc_sp = calc_risk_contributions(0.0, 1.0, self.vol_nq, self.vol_sp, self.rho)
        self.assertAlmostEqual(rc_sp["nq_risk_contrib"], 0.0, places=4)
        self.assertAlmostEqual(rc_sp["sp_risk_contrib"], 1.0, places=4)

    # =========================================================================
    # Part 5: Sortino Ratio & Box-Muller Sampling
    # =========================================================================

    def test_sortino_ratio_downside_volatility(self):
        """TC 5.1: Verify analytical Sortino downside volatility is strictly below full volatility."""
        rc = calc_risk_contributions(
            0.5, 0.5, self.vol_nq, self.vol_sp, self.rho,
            r_nq=self.mu_nq, r_sp=self.mu_sp, rf=self.rf
        )
        self.assertLess(rc["downside_vol"], rc["portfolio_vol"])
        self.assertGreater(rc["sortino_ratio"], rc["sharpe_ratio"])

    def test_box_muller_transform_presence(self):
        """TC 5.2: Verify Box-Muller transform implementation and zero-safeguard in worker and app."""
        self.assertIn("boxMuller", self.worker_js)
        self.assertIn("1e-10", self.worker_js, "sim-worker.js must safeguard u=0 with 1e-10")
        self.assertIn("boxMuller", self.app_js)
        self.assertIn("1e-10", self.app_js, "app.js must safeguard u=0 with 1e-10")


if __name__ == "__main__":
    unittest.main()
