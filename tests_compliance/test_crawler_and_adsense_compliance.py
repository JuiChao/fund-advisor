import os
import unittest
import json
import re
import glob


class TestCrawlerAndAdSenseCompliance(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.public_dir = os.path.join(self.root_dir, 'public')

    def test_adsense_distribution_and_crawler_policy(self):
        """AdSense compliance: utility/policy pages (404, privacy, terms, editorial) & fund pages
        must contain 0 AdSense code; fund pages must have noindex, follow;
        homepage and all 18 articles must retain AdSense meta tag and script.
        """
        zero_ads_pages = [
            os.path.join(self.public_dir, '404.html'),
            os.path.join(self.public_dir, 'privacy-policy.html'),
            os.path.join(self.public_dir, 'terms-of-service.html'),
            os.path.join(self.public_dir, 'editorial-policy.html'),
        ]
        for fpath in zero_ads_pages:
            self.assertTrue(os.path.exists(fpath), f"File {fpath} must exist")
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertNotIn('pagead2.googlesyndication.com', content, f"{fpath} must not contain AdSense script")
            self.assertNotIn('google-adsense-account', content, f"{fpath} must not contain AdSense account meta")

        # Fund pages: 0 AdSense and noindex, follow
        fund_files = glob.glob(os.path.join(self.public_dir, 'fund', '*.html'))
        self.assertEqual(len(fund_files), 60, "Expected 60 fund pages")
        for fpath in fund_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertNotIn('pagead2.googlesyndication.com', content, f"{fpath} must not contain AdSense script")
            self.assertNotIn('google-adsense-account', content, f"{fpath} must not contain AdSense account meta")
            self.assertIn('<meta name="robots" content="noindex, follow">', content, f"{fpath} must have noindex, follow firewall")

        # Homepage and 18 articles must retain AdSense
        index_path = os.path.join(self.public_dir, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            idx_content = f.read()
        self.assertIn('pagead2.googlesyndication.com', idx_content, "index.html must retain AdSense script")
        self.assertIn('google-adsense-account', idx_content, "index.html must retain AdSense account meta")

        article_files = [f for f in glob.glob(os.path.join(self.public_dir, 'articles', '*.html')) if not f.endswith('index.html')]
        self.assertEqual(len(article_files), 18, "Expected 18 research articles")
        for fpath in article_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                art_content = f.read()
            self.assertIn('pagead2.googlesyndication.com', art_content, f"{fpath} must retain AdSense script")
            self.assertIn('google-adsense-account', art_content, f"{fpath} must retain AdSense account meta")

    def test_sitelinks_searchbox_has_no_hash(self):
        """Item 5: Google Sitelinks Searchbox prohibits '#' in target."""
        index_path = os.path.join(self.public_dir, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'"potentialAction"\s*:\s*\{[^}]*"target"\s*:\s*"([^"]+)"', content)
        self.assertIsNotNone(match)
        target_url = match.group(1)
        self.assertEqual(target_url, 'https://858000.xyz/?q={query}')
        self.assertNotIn('#', target_url)

    def test_fund_pages_canonical_breadcrumbs(self):
        """Item 5: Fund pages must have a 2-level canonical breadcrumb without #ranking."""
        fund_files = glob.glob(os.path.join(self.public_dir, 'fund', '*.html'))
        self.assertGreater(len(fund_files), 0)
        for fpath in fund_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            # BreadcrumbList check
            self.assertIn('"@type": "BreadcrumbList"', content)
            self.assertNotIn('"https://858000.xyz/#ranking"', content)
            self.assertIn('"position": 1', content)
            self.assertIn('"position": 2', content)
            self.assertNotIn('"position": 3', content)

    def test_prefilled_static_baseline_values_in_index(self):
        """Item 6: index.html should not have '--' skeleton values for NDX and INX."""
        index_path = os.path.join(self.public_dir, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('id="ndx-price">26,958.76<', content)
        self.assertIn('id="ndx-badge">+1.24%<', content)
        self.assertIn('id="inx-price">7,374.71<', content)
        self.assertIn('id="inx-badge">+0.29%<', content)
        self.assertIn('id="ndx-etf-val">$655.74 (+1.34%)<', content)
        self.assertIn('id="inx-etf-val">$735.21 (+0.30%)<', content)

    def test_noscript_relocated_to_main_top(self):
        """Item 6: noscript block must be positioned near the top of main container."""
        index_path = os.path.join(self.public_dir, 'index.html')
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        main_pos = content.find('<main class="container">')
        noscript_pos = content.find('JavaScript 已禁用')
        page_home_pos = content.find('id="page-home"')
        self.assertNotEqual(main_pos, -1)
        self.assertNotEqual(noscript_pos, -1)
        self.assertNotEqual(page_home_pos, -1)
        self.assertTrue(main_pos < noscript_pos < page_home_pos)

    def test_redirects_for_single_page_routes(self):
        """Item 6: _redirects must contain 301 rules for hash route fallbacks."""
        redir_path = os.path.join(self.public_dir, '_redirects')
        self.assertTrue(os.path.exists(redir_path))
        with open(redir_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('/ranking /#ranking 301', content)
        self.assertIn('/simulator /#simulator 301', content)
        self.assertIn('/portfolio /#portfolio 301', content)
        self.assertIn('/guide /#guide 301', content)

    def test_localstorage_protected_in_html_files(self):
        """Item 3: All localStorage calls in HTML scripts must be guarded in try-catch."""
        html_files = [
            os.path.join(self.public_dir, 'index.html'),
            os.path.join(self.public_dir, 'about.html'),
            os.path.join(self.public_dir, 'editorial-policy.html'),
            os.path.join(self.public_dir, 'privacy-policy.html'),
            os.path.join(self.public_dir, 'terms-of-service.html'),
        ] + glob.glob(os.path.join(self.public_dir, 'articles', '*.html')) + glob.glob(os.path.join(self.public_dir, 'fund', '*.html'))

        for fpath in html_files:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Ensure every localStorage occurrence is wrapped in try
            for match in re.finditer(r'localStorage\.(getItem|setItem)', content):
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]
                self.assertIn('try', context, f"Unprotected localStorage in {fpath}")

    def test_app_js_switchpage_and_chart_guards(self):
        """Item 1 & Item 2: app.js switchPage resilience, Chart guards, and initTheme placement."""
        app_js_path = os.path.join(self.public_dir, 'js', 'app.js')
        with open(app_js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # switchPage resilience
        self.assertIn("target = document.getElementById('page-home');", content)
        self.assertIn("if (pName.startsWith('page-'))", content)
        self.assertIn("if (anchorEl) {", content)
        self.assertIn("const parentPage = anchorEl.closest('[id^=\"page-\"]');", content)

        # Chart undefined guards across all modules
        self.assertIn("if (typeof Chart !== 'undefined')", content)
        self.assertIn("if (typeof Chart === 'undefined')", content)
        # Check specific chart guards: frontier, stress, sim
        self.assertIn("if (typeof Chart === 'undefined') return;\n\n        // 创建 Chart.js 散点与折线图", content.replace('\r\n', '\n'))
        self.assertIn("if (typeof Chart === 'undefined') return;\n\n        const isDark", content.replace('\r\n', '\n'))

        # currentExportTheme try/catch
        self.assertIn("try {\n        currentExportTheme = localStorage.getItem('fa_export_theme')", content.replace('\r\n', '\n'))

        # initTheme inside try
        self.assertIn("async function init() {\n        try {\n            initTheme();", content.replace('\r\n', '\n'))

    def test_high_quality_sitemap_compliance(self):
        """High-quality priority sitemap must exist, be valid XML, contain exactly 24 URLs,
        and have zero /fund/ programmatic URLs.
        """
        import xml.etree.ElementTree as ET
        hq_sitemap = os.path.join(self.public_dir, 'sitemap-high-quality.xml')
        self.assertTrue(os.path.exists(hq_sitemap), "public/sitemap-high-quality.xml must exist")
        tree = ET.parse(hq_sitemap)
        root = tree.getroot()
        self.assertIn("urlset", root.tag)
        urls = [loc.text for loc in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertEqual(len(urls), 24, f"High quality sitemap must contain exactly 24 URLs, found {len(urls)}")
        self.assertIn("https://858000.xyz/", urls)
        self.assertIn("https://858000.xyz/articles/", urls)
        self.assertIn("https://858000.xyz/about", urls)
        self.assertIn("https://858000.xyz/editorial-policy", urls)
        self.assertIn("https://858000.xyz/privacy-policy", urls)
        self.assertIn("https://858000.xyz/terms-of-service", urls)
        for u in urls:
            self.assertNotIn("/fund/", u, f"High quality sitemap must not contain programmatic fund pages: {u}")

    def test_zero_scraper_vocabulary_in_public(self):
        """Purge '抓取' / '采集' site-wide: public HTML pages and app.js must not contain scraper phrasing."""
        target_files = [
            os.path.join(self.public_dir, 'index.html'),
            os.path.join(self.public_dir, 'about.html'),
            os.path.join(self.public_dir, 'editorial-policy.html'),
            os.path.join(self.public_dir, 'privacy-policy.html'),
            os.path.join(self.public_dir, 'terms-of-service.html'),
            os.path.join(self.public_dir, 'js', 'app.js'),
        ] + glob.glob(os.path.join(self.public_dir, 'articles', '*.html')) + glob.glob(os.path.join(self.public_dir, 'fund', '*.html'))

        forbidden_words = ['抓取', '采集']
        for fpath in target_files:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            for kw in forbidden_words:
                self.assertNotIn(kw, content, f"File {fpath} must not contain '{kw}'")


if __name__ == '__main__':
    unittest.main()
