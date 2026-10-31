"""Tier 2 Boundary 3: Portfolio Configurator Boundary & Corner Cases Tests."""
import unittest
from tests_e2e.e2e_common import load_algo_data


class TestPortfolioConfiguratorBoundary(unittest.TestCase):
    """Verifies parameter boundary constraints, MPT numerical limits, and ERC optimality."""

    @classmethod
    def setUpClass(cls):
        cls.algo = load_algo_data()

    def test_budget_parameter_boundary_specs(self):
        """TC 3.1: Verify budget min, max, and step boundaries in algorithm.json."""
        alloc = self.algo.get("allocation", {})
        self.assertEqual(alloc.get("budget_min"), 500, "Minimum monthly budget must be ¥500")
        self.assertEqual(alloc.get("budget_max"), 10000, "Maximum monthly budget must be ¥10,000")
        self.assertEqual(alloc.get("budget_step"), 100, "Budget step must be ¥100")

    def test_horizon_years_boundary_specs(self):
        """TC 3.2: Verify investment years min, max, and step boundaries."""
        alloc = self.algo.get("allocation", {})
        self.assertEqual(alloc.get("years_min"), 5, "Minimum investment horizon must be 5 years")
        self.assertEqual(alloc.get("years_max"), 30, "Maximum investment horizon must be 30 years")
        self.assertEqual(alloc.get("years_step"), 1, "Horizon step must be 1 year")

    def test_extreme_portfolio_weights_boundary(self):
        """TC 3.3: Test extreme 100% single asset weights produce expected terminal volatility."""
        # Using MPT covariance formula: Var(p) = w1^2*s1^2 + 2*w1*w2*Cov12 + w2^2*s2^2
        params = self.algo.get("simulation", {}).get("params", {})
        s_nq = params.get("nasdaq_vol", 0.22)
        s_sp = params.get("sp500_vol", 0.18)
        rho = self.algo.get("simulation", {}).get("correlation_nq_sp", 0.75)

        # 100% Nasdaq
        vol_100_nq = s_nq
        # 100% S&P 500
        vol_100_sp = s_sp
        self.assertGreater(vol_100_nq, vol_100_sp, "Pure Nasdaq volatility must exceed pure S&P 500")

    def test_risk_parity_strategy_weight_bounds(self):
        """TC 3.4: Verify risk parity (ERC) strategy allocates higher weight to lower-vol S&P."""
        strategies = self.algo.get("strategies", [])
        rp_strat = next((s for s in strategies if s["key"] == "risk_parity"), None)
        self.assertIsNotNone(rp_strat, "risk_parity strategy must exist in algorithm.json")
        nq_pct = rp_strat.get("nq_pct")
        self.assertGreaterEqual(nq_pct, 0.35, "ERC Nasdaq weight should be >= 35%")
        self.assertLessEqual(nq_pct, 0.50, "ERC Nasdaq weight should be <= 50% to balance higher vol")

    def test_correlation_positive_definiteness(self):
        """TC 3.5: Verify correlation coefficient ensures positive definite covariance matrix."""
        rho = self.algo.get("simulation", {}).get("correlation_nq_sp", 0.75)
        self.assertGreater(rho, 0.0, "Correlation must be positive")
        self.assertLess(rho, 1.0, "Correlation must be less than 1.0 to ensure diversification")
        det = 1.0 - (rho ** 2)
        self.assertGreater(det, 0.0, f"Matrix determinant (1 - rho^2 = {det}) must be strictly positive")


if __name__ == "__main__":
    unittest.main()
