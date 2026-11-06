"""Tier 1 Feature 13: Hero Indices Deck & Black Swan Alert Module Tests."""
import json
import os
import re
import unittest
from pathlib import Path
from tests_e2e.e2e_common import load_index_soup, load_style_css, load_app_js

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestHeroIndicesModule(unittest.TestCase):
    """Verifies the DOM structure, CSS styling, responsive layout, and JS contracts

    for the Nasdaq 100 & S&P 500 Live Quotes and Black Swan Alert Deck.
    """

    @classmethod
    def setUpClass(cls):
        cls.soup = load_index_soup()
        cls.css = load_style_css()
        cls.js = load_app_js()
        indices_js_path = PROJECT_ROOT / "functions" / "api" / "indices.js"
        with open(indices_js_path, "r", encoding="utf-8") as f:
            cls.indices_js = f.read()

        fallback_path = PROJECT_ROOT / "public" / "data" / "indices_fallback.json"
        with open(fallback_path, "r", encoding="utf-8") as f:
            cls.fallback_data = json.load(f)

    def test_dom_deck_injection_and_topology(self):
        """TC 13.1: Verify #hero-indices-deck is placed directly under .ticker-header-bar without disturbing 5 pods."""
        ticker = self.soup.find(id="hero-quant-ticker")
        self.assertIsNotNone(ticker, "#hero-quant-ticker must exist")

        hdr = ticker.find(class_="ticker-header-bar")
        self.assertIsNotNone(hdr, ".ticker-header-bar must exist")

        deck = ticker.find(id="hero-indices-deck")
        self.assertIsNotNone(deck, "#hero-indices-deck must exist")

        sibling = hdr.find_next_sibling()
        self.assertEqual(sibling.get("id"), "hero-indices-deck",
                         "hero-indices-deck must be immediate next sibling after ticker-header-bar")

        # Confirm original 5 KPI pods are preserved
        pods = ticker.find_all(class_="ticker-box")
        self.assertEqual(len(pods), 5, f"Expected 5 original .ticker-box elements, got {len(pods)}")

    def test_dual_core_cards_elements(self):
        """TC 13.2: Verify dual core cards for ^NDX and ^GSPC with all indicators and accessibility."""
        cards = {
            "ndx": ("card-index-ndx", "^NDX · QQQ", "QQQ"),
            "inx": ("card-index-inx", "^GSPC · SPY", "SPY")
        }

        for prefix, (card_id, symbol_text, etf_sym) in cards.items():
            card = self.soup.find(id=card_id)
            self.assertIsNotNone(card, f"#{card_id} must exist in DOM")
            self.assertIn(symbol_text, card.get_text(), f"Card #{card_id} must display {symbol_text}")

            # Price, Badge, Diff
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-price"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-badge"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-diff"))

            # ETF live price tag
            etf_val = self.soup.find(id=f"{prefix}-etf-val")
            self.assertIsNotNone(etf_val)

            # Range Bar and ARIA progressbar
            track = self.soup.find(id=f"{prefix}-range-bar")
            self.assertIsNotNone(track, f"Range bar track #{prefix}-range-bar must exist")
            self.assertEqual(track.get("role"), "progressbar", "Range track must have role=progressbar")
            self.assertIsNotNone(track.get("aria-valuenow"), "Range track must have aria-valuenow")

            # High, Low, Range %
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-low"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-high"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-range-pct"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-range-fill"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-range-marker"))

            # Extended session & NAV lag tip
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-ext-wrap"))
            self.assertIsNotNone(self.soup.find(id=f"{prefix}-lag-text"))

    def test_black_swan_banner_structure_and_cta(self):
        """TC 13.3: Verify Black Swan Banner ARIA attributes, headline, and #portfolio CTA."""
        banner = self.soup.find(id="black-swan-banner")
        self.assertIsNotNone(banner, "#black-swan-banner must exist")
        self.assertEqual(banner.get("role"), "alert")
        self.assertEqual(banner.get("aria-live"), "assertive")

        cta = self.soup.find(id="swan-cta-btn")
        self.assertIsNotNone(cta, "#swan-cta-btn must exist")
        self.assertEqual(cta.get("href"), "#portfolio", "CTA button must route to #portfolio")

    def test_css_grid_and_award_tier_styling(self):
        """TC 13.4: Verify CSS grid-column: 1 / -1, animations, and responsive breakpoints."""
        self.assertIn(".hero-indices-deck", self.css)
        self.assertTrue(re.search(r"\.hero-indices-deck\s*\{[^}]*grid-column\s*:\s*1\s*/\s*-1", self.css))
        self.assertTrue(re.search(r"\.hero-indices-deck\s*\{[^}]*width\s*:\s*100%", self.css))

        # Desktop 2-column grid
        self.assertTrue(re.search(r"\.indices-grid\s*\{[^}]*grid-template-columns\s*:\s*repeat\(2,\s*1fr\)", self.css))

        # Mobile single column stack on <=768px
        self.assertTrue(re.search(r"@media[^{]*max-width\s*:\s*768px[^{]*\{[\s\S]*?\.indices-grid\s*\{[^}]*grid-template-columns\s*:\s*1fr", self.css))

        # Compact mobile adjustments on <=480px
        self.assertTrue(re.search(r"@media[^{]*max-width\s*:\s*480px", self.css))

        # Keyframe animations
        self.assertIn("@keyframes priceFlashUp", self.css)
        self.assertIn("@keyframes priceFlashDown", self.css)
        self.assertIn(".price-flash-up", self.css)
        self.assertIn(".price-flash-down", self.css)

    def test_functions_api_contract_and_cache_headers(self):
        """TC 13.5: Verify Cloudflare Pages Function /api/indices implementation and fallback JSON."""
        self.assertIn("export async function onRequest", self.indices_js)
        self.assertIn("Cache-Control", self.indices_js)
        self.assertIn("max-age=15", self.indices_js)
        self.assertIn("s-maxage=20", self.indices_js)
        self.assertIn("stale-while-revalidate=40", self.indices_js)
        self.assertIn("https://qt.gtimg.cn/q=usNDX,usINX,usQQQ,usSPY", self.indices_js)

        # Verify fallback JSON schema
        self.assertTrue(self.fallback_data.get("success"))
        self.assertIn("indices", self.fallback_data)
        self.assertEqual(self.fallback_data["indices"]["NDX"]["symbol"], "^NDX")
        self.assertEqual(self.fallback_data["indices"]["INX"]["symbol"], "^GSPC")

    def test_app_js_state_machine_and_countdown_contract(self):
        """TC 13.6: Verify app.js smart polling, market open countdown, and multi-tier disaster recovery."""
        self.assertIn("initHeroIndicesStream()", self.js)
        self.assertIn("visibilitychange", self.js)
        self.assertIn("document.visibilityState === 'hidden'", self.js)
        self.assertIn("document.visibilityState === 'visible'", self.js)
        self.assertIn("/api/indices", self.js)
        self.assertIn("https://qt.gtimg.cn/q=usNDX,usINX,usQQQ,usSPY", self.js)
        self.assertIn("/data/indices_fallback.json", self.js)

        # Confirm countdown logic is present
        self.assertIn("updateClosedCountdownUI", self.js)
        self.assertIn("距美股开盘倒计时", self.js)

        # Confirm Black Swan thresholds
        self.assertIn("minDrop <= -3.0", self.js)
        self.assertIn("minDrop <= -5.0", self.js)
        self.assertIn("inxDrop <= -7.0", self.js)


if __name__ == "__main__":
    unittest.main()
