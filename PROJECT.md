# Project: Fund Advisor Institutional Quantitative Terminal & Modern Web Optimization

## Architecture
Fund Advisor (https://858000.xyz) is a production quantitative index fund DCA terminal designed with pure vanilla zero-build architecture.
- **Frontend Presentation Layer (`public/css/style.css`)**: Centralized design system tokens, typography rules, layout primitives, responsive viewports, and theme styling.
- **Frontend Markup Layer (`public/index.html`, `public/about.html`)**: Core single-page quant terminal containing 5 views (`#page-home`, `#page-ranking`, `#page-portfolio`, `#page-simulator`, `#page-guide`), telemetry HUD, quotes deck, and accessible dialog modals.
- **Application Logic Layer (`public/js/app.js`, `public/js/sim-worker.js`)**: Pure vanilla JS application runtime, Chart.js controller, Monte Carlo simulation engine, Page Visibility API energy conservation, and DOM event bindings.
- **Content & Generation Layer (`public/articles/`, `scraper/generate_seo.py`, `public/fund/`)**: Static financial engineering research articles and automated Python SEO generator that pre-renders 60 fund evaluation pages and sitemap.
- **Test Infrastructure (`tests/`, `tests_e2e/`, `tests_compliance/`)**: 4-tier test runner (309 checks), 94 baseline unit tests, 8 AdSense/crawler compliance tests, and Tier-5 layout adversarial stress tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Elimination of Cheap Gradients | Remove token-level, hero, title text-clip, and multi-stop gradient blobs in favor of matte surfaces | M1 | Survey (R1) |
| 2 | Removal of Ambient Glow Meshes | Eliminate `.ambient-glow-mesh` DOM clusters across index, about, 18 articles, 60 fund pages, and `generate_seo.py` | M2, M4 | Survey (R1) |
| 3 | Elimination of Decorative Emojis & Arrows | Replace 44+ unicode arrows (`➔`), hardcoded rating stars, and decorative glyphs with clean SVGs/tabular indicators | M2, M3 | Survey (R1) |
| 4 | Neutral Institutional Microcopy Overhaul | Strip hype marketing claims ("华尔街对冲基金级", "击碎择时神话", "Awwwards/Webby compliant") in favor of restrained quant phrasing | M2 | Survey (R1) |
| 5 | Tightened Corner Radii & Border Refinements | Replace 9999px bubble pills with crisp 2px-4px rounded rectangles; 1px crisp borders for high-density terminal look | M1 | Survey (R1) |
| 6 | High-Density Tabular Presentation | Compact table cell padding (8px 12px), right-aligned monospace numbers with `font-variant-numeric: tabular-nums` | M1 | Survey (R1) |
| 7 | Speculation Rules Integration | Add `<script type="speculationrules">` with prefetch and prerender rules across all pages and generator template | M2, M4 | Survey (R2) |
| 8 | `content-visibility: auto` Render Deferral | Apply `content-visibility: auto` + `contain-intrinsic-size` to offscreen lists, tables, EEAT cards, and footer | M1 | Survey (R2) |
| 9 | Modern Typography Wrapping | Apply `text-wrap: balance` to headings and `text-wrap: pretty` to body paragraphs and review copy | M1 | Survey (R2) |
| 10 | Native `color-scheme` & Dual Theming | Declare `<meta name="color-scheme" content="light dark">` in `<head>`, `:root { color-scheme: light dark; }`, and `scrollbar-color` | M1, M2 | Survey (R2) |
| 11 | Scroll-Driven Affordance Hints | Maintain horizontal touch-scroll indicator masks on table wraps and CSS scroll progress bar with passive fallback | M1 | Survey (R2) |
| 12 | Page Visibility API Energy Conservation | Guard animation RAF loops, chart updates, and high-frequency ping/countdown intervals behind `document.visibilityState` | M3 | Survey (R2) |
| 13 | Accessible Native `<dialog>` Modals | Upgrade 4 custom modal backdrops to native `<dialog>` elements with `showModal()`, light dismiss, and scroll containment | M2, M3 | Survey (R2) |
| 14 | Scraper Generator Pipeline Modernization | Update `scraper/generate_seo.py` template with unslop design and modern web standards; regenerate 60 fund pages & sitemap | M4 | Survey (R1, R2) |
| 15 | Research Articles Fleet Modernization | Upgrade all 18 static research articles in `public/articles/*.html` with unslop layout, clean SVGs, and speculation rules | M4 | Survey (R1, R2) |
| 16 | Test Contract & Semantic Preservation | Guarantee 100% preservation of all 88 DOM element IDs, 45 core CSS classes, 6 ARIA roles, and cache token `?v=20261031_award` | M1, M2, M3, M4, M5 | Survey (R4) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Design System & CSS Modernization | `public/css/style.css`: Unslop color tokens, 1px crisp borders, 2px-4px radii, table density, `content-visibility`, `text-wrap`, native `color-scheme`, `scrollbar-color`, preserving `@keyframes pulseGlow/pulseGlowAura` and contracted classes | none | DONE |
| M2 | Core Terminal Frontend Modernization | `public/index.html`, `public/about.html`: Remove ambient glow mesh, inline gradients, hype copy, unicode arrows; inject `<meta name="color-scheme">`, Speculation Rules, native `<dialog>` elements, preserving all 88 IDs and static ticker baselines | M1 | DONE |
| M3 | Client Logic & Performance Modernization | `public/js/app.js`: Page Visibility API integration (pause RAF canvas loop and timers when tab is hidden), native `<dialog>` management with light dismiss, clean dynamic badge renderers, preserving all event bindings and calculation contracts | M2 | DONE |
| M4 | Articles Fleet & Scraper Modernization | `scraper/generate_seo.py`, `public/articles/*.html`, `public/fund/*.html`: Modernize Python generator template; regenerate all 60 fund dossiers and `sitemap.xml`; update all 18 static articles with unslop aesthetic, table wrappers, and speculation rules | M1, M2 | DONE |
| M5 | Final Verification & Adversarial Hardening | Phase 1: 100% pass across all 94 unit tests, 309 E2E checks, 8 compliance tests, 20 Tier-5 layout tests, 0 Node syntax errors. Phase 2: Tier-5 adversarial coverage hardening with Challenger -> Worker -> Reviewer loop | M1, M2, M3, M4 | DONE |

## Code Layout
- `public/css/style.css`: Owned exclusively by Milestone 1 Worker (DONE).
- `public/index.html`, `public/about.html`: Owned exclusively by Milestone 2 Worker.
- `public/js/app.js`: Owned exclusively by Milestone 3 Worker.
- `scraper/generate_seo.py`, `public/articles/*.html`, `public/fund/*.html`, `public/sitemap.xml`: Owned exclusively by Milestone 4 Worker.
- Concurrent workers must NOT write to each other's owned files.

## Interface Contracts
### M1 ↔ M2, M3, M4 (CSS Tokens & Classes)
- **Token Preservations**: `:root` and `[data-theme='dark']` define: `--up`, `--down`, `--table-hover-bg`, `--surface`, `--surface2`, `--txt`, `--border`, `--border2`, `--accent`, `--bg`, `--bg2`, `--card`, `--shadow-md`, `--radius-sm` (3px), `--radius-md` (4px).
- **Keyframe Preservations**: Exactly one `@keyframes pulseGlow` and one `@keyframes pulseGlowAura` in `style.css`.
- **Selector Preservations**: All 45 critical CSS classes (e.g. `.table-wrap`, `.dir-table-wrap`, `.quota-table-wrap`, `.ticker-box`, `.indices-grid`, `.badge-relaxed`, `.badge-tightened`, `.badge-div`, `.eeat-author-card`, `.article-takeaways-card`) preserved.
- **Cache Query Consistency**: All HTML files MUST link to `/css/style.css?v=20261031_award`.

### M2 ↔ M3 (DOM IDs & Dialog Interfaces)
- **Dialog Elements**: `#rank-select-modal`, `#quota-select-modal`, `#poster-modal-backdrop`, `#shortcut-hud-modal` upgrade from plain divs to native `<dialog>` elements or retain their exact IDs with accessible attributes so `app.js` can call `.showModal()` with fallback.
- **Input & Trigger IDs**: Preserved verbatim: `#rank-table`, `#btn-pf`, `#btn-sim`, `#sim-m`, `#sim-y`, `#pf-m`, `#pf-y`, `#theme-toggle`, `#quota-alert-bar`, `#btn-quota-toggle`, etc.
- **Static Baseline Values**: `#ndx-price` ("26,958.76"), `#ndx-badge` ("+1.24%"), `#inx-price` ("7,374.71"), `#inx-badge` ("+0.29%"), `#ndx-etf-val` ("$655.74 (+1.34%)"), `#inx-etf-val` ("$735.21 (+0.30%)"), `#qstat-stable` ("60").

### M4 ↔ M1, M2 (Scraper Output & Articles Contracts)
- **Table Wrapping**: Every data table in articles and fund pages MUST be wrapped in `.table-wrap` or `.dir-table-wrap`.
- **Breadcrumb JSON-LD**: Exactly 2 levels in `fund/{code}.html` (Position 1: "首页", Position 2: `{fund_name}`), without `#ranking`.
- **File System Safety**: `scraper/generate_seo.py` MUST maintain `ignore_errors=True` on folder recreation to prevent Windows file-lock errors.
- **Article Schema**: `@type: Article` with publisher/author attributed to "Fund Advisor".
