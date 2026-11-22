# Project: Fund Advisor Institutional Quantitative Terminal (stitch-skills Redesign)

## Architecture
Fund Advisor (https://858000.xyz) is a production quantitative index fund DCA terminal designed with pure vanilla zero-build architecture.
- **Frontend Presentation Layer (`public/css/style.css`)**: Centralized design system tokens, typography rules, layout primitives, responsive viewports, and theme styling adhering to stitch-skills / DESIGN.md standards.
- **Frontend Markup Layer (`public/index.html`, `public/about.html`)**: Core single-page quant terminal containing 5 views (`#page-home`, `#page-ranking`, `#page-portfolio`, `#page-simulator`, `#page-guide`), telemetry HUD, quotes deck, and accessible dialog modals.
- **Application Logic Layer (`public/js/app.js`, `public/js/sim-worker.js`)**: Pure vanilla JS application runtime, Chart.js controller, Monte Carlo simulation engine, Page Visibility API energy conservation, and DOM event bindings.
- **Content & Generation Layer (`public/articles/`, `scraper/generate_seo.py`, `public/fund/`)**: Static financial engineering research articles and automated Python SEO generator that pre-renders 60 fund evaluation pages and sitemaps.
- **Test Infrastructure (`tests/`, `tests_e2e/`, `tests_compliance/`)**: 4-tier test runner (309 checks), 94 baseline unit tests, 10 AdSense/crawler compliance tests, and Tier-5 layout & engine adversarial stress tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Stitch Design Tokens & Tiered Surface Hierarchy | 3-4 tier surface hierarchy (`--bg`, `--surface`, `--surface-raised`, `--surface2`), WCAG 2.1 AA luminous dark/light contrast | M1 | Survey (R1) |
| 2 | Pure Local System Font Stack Standardization | Zero external font requests; standardize high-craft local system fonts with universal `tabular-nums lining-nums` | M1 | Survey (R1, R2) |
| 3 | Tactile Micro-Interactions & Focus Accessibility | Tactile depressions (`scale(0.98)` / `translateY(1px)` on active), accessible 2px `:focus-visible` rings across all controls | M1 | Survey (R1) |
| 4 | High-Density Institutional Quant Table Styling | Compact 8px cell padding, crisp 1px borders, right-aligned tabular numerals, sticky column elevation | M1 | Survey (R1) |
| 5 | Quota Intelligence Radar Drawer & Alert Styling | Refined animated SVG radar reticle, smooth drawer transition, high-contrast status pills | M1, M2 | Survey (R1) |
| 6 | Telemetry HUD & Quotes Deck Visual Upgrade | High-density typography, live session indicators, countdown pill, zero-layout-shift price refresh | M2 | Survey (R1) |
| 7 | Black Swan Alert Banner Institutional Refinement | Subtle pulsating edge highlight, clean SVG warning icons (-3%, -5%, -7%), direct portfolio CTA | M2 | Survey (R1) |
| 8 | Accessible Native Dialog Modals | Native `<dialog>` semantics with `showModal()`, blur backdrop (`backdrop-filter`), light dismiss on backdrop click | M2, M3 | Survey (R1) |
| 9 | About Page AdSense Cleanliness (0-Ads Compliance) | Remove lingering AdSense tags from `public/about.html` to strictly satisfy zero-ads compliance | M2 | Survey (R3) |
| 10 | MPT Frontier Synchronized Slider & Variance Bars | Smooth slider-to-canvas cursor synchronization, clear capital vs variance divergence bars, matrix row jump | M3 | Survey (R1) |
| 11 | Monte Carlo Wealth Simulator Computing Deck Polish | Preset tag buttons (`[ERC]`, `[MVO]`), precision steppers, computing shimmer, dynamic DCA Alpha excess card | M3 | Survey (R1) |
| 12 | Historical Crisis Stress Testing UI Elevation | Sleek segmented tab controls, clean crisis trough marker, compact recovery months table | M3 | Survey (R1) |
| 13 | 18 Research Articles Fleet Visual Elevation | Modern typography hierarchy, `text-wrap: balance/pretty`, callout blocks, takeaways cards, `.table-wrap` | M4 | Survey (R1, R3) |
| 14 | Scraper Generator Pipeline Layout Upgrade | Modernize `scraper/generate_seo.py` template, regenerate 60 fund pages with `.dir-table-wrap`, update sitemaps | M4 | Survey (R1, R3) |
| 15 | Strict Contract Preservation & Full Regression Guard | Preserve all 88 DOM IDs, 7 static ticker baselines, 10 table headers, `?v=20261031_award`, 100% test pass | M1, M2, M3, M4, M5 | Survey (R4) |
| 16 | Final E2E Regression, Adversarial Verification & Audit | 100% pass across all 94 unit, 10 compliance, 309 E2E tests, Tier-5 adversarial stress suites, Forensic audit | M5 | Survey (R4) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Design System & CSS Token Modernization | `public/css/style.css`: Stitch-skills tokens, 3-4 tier surfaces, local system fonts, tabular numerals, 1px crisp borders, tactile micro-interactions (`:focus-visible`, `active`), preserving fluid clamps, keyframes (`pulseGlow`/`pulseGlowAura`), and all contracted selectors | none | DONE |
| M2 | Core Terminal Frontend Modernization | `public/index.html`, `public/about.html`: Telemetry HUD, quotes deck, black swan banner, SVG sort indicators, native `<dialog>` elements, strip AdSense from `about.html`, preserving all 88 DOM IDs, 7 static baseline fixtures, and JSON-LD | M1 | DONE |
| M3 | Client Quantitative Logic & Dynamic Visualizations | `public/js/app.js`, `public/js/sim-worker.js`: Synchronized MPT slider feedback, Monte Carlo computing deck & dynamic DCA alpha presentation, native `<dialog>` showModal management, Page Visibility API | M2 | DONE |
| M4 | Articles Fleet & Scraper Generator Modernization | `scraper/generate_seo.py`, `public/articles/*.html`, `public/fund/*.html`: Modernize Python generator template; regenerate 60 fund pages and dual sitemaps; update all 18 static research articles with stitch-skills typography, preserving `.table-wrap` and font comments | M1, M2 | DONE |
| M5 | Final Verification, Adversarial Hardening & Forensic Audit | Phase 1: 100% pass across all 94 unit tests, 10 compliance tests, 309 E2E checks, Tier-5 layout and engine suites. Phase 2: Adversarial stress verification and Forensic Auditor clean verdict | M1, M2, M3, M4 | DONE |

## Code Layout
- `public/css/style.css`: Owned exclusively by Milestone 1 Worker (DONE).
- `public/index.html`, `public/about.html`: Owned exclusively by Milestone 2 Worker (DONE).
- `public/js/app.js`, `public/js/sim-worker.js`: Owned exclusively by Milestone 3 Worker.
- `scraper/generate_seo.py`, `public/articles/*.html`, `public/fund/*.html`, `public/sitemap.xml`, `public/sitemap-high-quality.xml`: Owned exclusively by Milestone 4 Worker.
- Concurrent workers must NOT write to each other's owned files.

## Interface Contracts
### M1 ↔ M2, M3, M4 (CSS Tokens & Classes)
- **Token Preservations**: `:root, [data-theme='light']` and `[data-theme='dark']` MUST define: `--up`, `--down`, `--table-hover-bg`, `--surface`, `--surface2`, `--txt`, `--border`, `--border2`, `--accent`, `--bg`, `--bg2`, `--card`, `--shadow-md`, `--radius-sm`, `--radius-md`.
- **Fluid Clamp Formulas**: Must preserve exact fluid typography clamps for `--font-size-hero`, `--font-size-h1`, `--font-size-h2`, `--font-size-body`.
- **Keyframe Uniqueness**: Exactly one `@keyframes pulseGlow` and one `@keyframes pulseGlowAura` in `style.css`. Preserve `priceFlashUp`, `priceFlashDown`, `simShimmer`, `simSpin`.
- **Selector Preservations**: All critical CSS classes (`.table-wrap`, `.dir-table-wrap`, `.quota-table-wrap`, `.ticker-box`, `.indices-grid`, `.badge-relaxed`, `.badge-tightened`, `.badge-div`, `.eeat-author-card`, `.article-takeaways-card`, `.fund-select-modal-backdrop`, `.poster-modal-backdrop`, `.hero-quant-ticker`) preserved.
- **Cache Query Token**: All HTML files MUST link to `/css/style.css?v=20261031_award`.

### M2 ↔ M3 (DOM IDs & Dialog Interfaces)
- **Dialog Elements**: `#rank-select-modal`, `#quota-select-modal`, `#poster-modal-backdrop`, `#shortcut-hud-modal` must support native `<dialog>` with `.showModal()` while keeping their exact IDs and classes.
- **Input & Trigger IDs**: Preserved verbatim: `#rank-table`, `#btn-pf`, `#btn-sim`, `#sim-m`, `#sim-y`, `#pf-m`, `#pf-y`, `#theme-toggle`, `#quota-alert-bar`, `#btn-quota-toggle`, `#frontier-range-slider`, `#sim-smart-toggle`, etc.
- **Static Baseline Values**: `#ndx-price` ("26,958.76"), `#ndx-badge` ("+1.24%"), `#inx-price` ("7,374.71"), `#inx-badge` ("+0.29%"), `#ndx-etf-val` ("$655.74 (+1.34%)"), `#inx-etf-val` ("$735.21 (+0.30%)"), `#qstat-stable` ("60").
- **Table Header Rendering Alignment**: `renderRankTable()` in `app.js` should render matching accessible SVG sort chevrons or preserve the header SVG elements created in M2.

### M4 ↔ M1, M2 (Scraper Output & Articles Contracts)
- **Table Wrapping**: Every data table in articles MUST be wrapped in `.table-wrap`. Every data table in fund pages MUST be wrapped in `.dir-table-wrap`.
- **Breadcrumb JSON-LD**: Exactly 2 levels in `fund/{code}.html` (Position 1: "首页", Position 2: `{fund_name}`), without `#ranking`.
- **Font Comment**: All articles MUST retain `<!-- Native system font stack with local JetBrains+Mono fallback -->`.
- **Vocabulary**: Zero occurrences of "抓取" or "采集" across all public files.
- **File System Safety**: `scraper/generate_seo.py` MUST maintain `ignore_errors=True` on folder recreation.
