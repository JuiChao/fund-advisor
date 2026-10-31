# Project: fund-advisor Award-Tier Visual & Design Overhaul

## Architecture
- **Pure Native Frontend**: HTML5, Modern CSS3 with Custom Properties, Vanilla JavaScript (ES6+), Web Workers. Zero build steps, bundlers, or heavy frameworks (strictly adhering to Requirement R2).
- **Core Assets**:
  - `public/index.html`: Main SPA containing the telemetry HUD and 5 core quantitative modules.
  - `public/css/style.css`: Unified stylesheet with design tokens, themes, typography, layout, and component styles.
  - `public/js/app.js`: IIFE application core managing state, DOM events, MPT math, and rendering.
  - `public/js/sim-worker.js`: Web Worker executing 5,000-run Monte Carlo simulations.
  - `public/about.html`: About and methodology page.
  - `public/articles/*.html`: 18 quantitative research reports and index hub.
  - `public/fund/*.html`: 60 individual fund detail pages generated programmatically.
  - `scraper/generate_seo.py`: Programmatic SEO generator for fund detail pages and sitemap.xml.
  - `tests/`: 94 Python unit tests verifying quant algorithms and data integrity.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Design System & Token Architecture | Unified CSS custom properties for colors, elevation, border-radius, typography, and spacing; fix missing `--up`/`--down` variables; fix unmapped raw hexes | M1 | Survey 1 |
| 2 | Keyframe Animation Collision Fix | Resolve duplicate `@keyframes pulseGlow` collisions between line 9529 and line 9913 in `style.css` | M1 | Survey 1 |
| 3 | Fluid Responsive Typography Scale | Restore responsive fluid typography clamp on headings and fix 768px media query override forcing 1.5rem | M1 | Survey 1 |
| 4 | Dark/Light Dual Theme Polish | Sophisticated financial dark mode and crisp high-contrast light mode adhering to WCAG AAA contrast ratios | M1 | Survey 1 |
| 5 | Real-Time Telemetry HUD Overhaul | US Eastern Time HUD styling, session status badges, animated status pulse dot, odometer tickers, latency gauge | M1 | Survey 1 & 2 |
| 6 | Navigation & Top Header Polish | Glassmorphism navigation bar, responsive mobile drawer, active link indicators, smooth theme switch micro-interactions | M1 | Survey 1 & 2 |
| 7 | DOM ID Mismatch Fix | Fix `quota-bulletin-section` vs `quota-bulletin-container` mismatch between `app.js:471` and `index.html:1149` to restore CTA smooth scrolling | M2 | Survey 2 |
| 8 | 60-Target Quantitative Matrix Table (#rank-table) | Award-tier table styling, sticky header, tabular numbers (`tabular-nums`), interactive sort/filter states, drawer accordion polish, mobile card view | M2 | Survey 2 |
| 9 | MPT Portfolio Configurator (#portfolio) | Visual overhaul of asset allocation sliders, glow tracks, efficient frontier chart container, stress test cards, risk contribution bars | M2 | Survey 2 |
| 10 | 5,000-Run Monte Carlo Simulator (#simulator) | High-fidelity parameter controls, smooth progress indicator, distribution chart container, probability ladder cards, odometer count-up numbers | M2 | Survey 2 |
| 11 | Market Restriction Radar (#radar) | Quota radar cards, dynamic status tags, animated radar ping ring, quota sharing badges, canvas poster export visual polish | M2 | Survey 2 |
| 12 | Safe JS Selector Coupling | Adhere strictly to 159 IDs, 66 query selectors, and 16 event listeners mapped in `survey_report.md` to prevent any functional regression | M2 | Survey 2 |
| 13 | About Page Visual Elevation | Redesign `public/about.html` layout, methodology cards, credentials, responsive grid, and typography | M3 | Survey 3 |
| 14 | Research Articles Reading Experience (18 files) | Standardize typography, replace absolute production URLs with root-relative paths, add `.table-wrap` for 7 unwrapped tables, add executive takeaways card | M3 | Survey 3 |
| 15 | Programmatic Fund Detail Generator Upgrade | Refactor `scraper/generate_seo.py` HTML template: replace legacy footer with `.footer-inner`, eliminate inline styles, apply semantic tokens, regenerate 60 fund pages | M3 | Survey 3 |
| 16 | Cache-Busting Version Query Unification | Synchronize `?v=20261031_award` across `index.html`, `about.html`, `articles/*.html`, and `generate_seo.py` | M3 | Survey 1 & 3 |
| 17 | Multi-Viewport E2E Test Infrastructure | Requirement-driven opaque-box test runner validating mobile (375px), tablet (768px), and desktop (1440px) without overflow or regression | M4 | Project Pattern |
| 18 | E2E Tier 1: Feature Coverage Tests | >=5 test cases per feature verifying baseline rendering, selectors, calculations, and navigation | M4 | Project Pattern |
| 19 | E2E Tier 2: Boundary & Corner Cases | Viewport boundary checks (375px/768px/1440px), empty filters, extreme portfolio weights, rapid clicks | M4 | Project Pattern |
| 20 | E2E Tier 3: Cross-Feature Interactions | Combinatorial tests: theme toggle + table filter + sorting, portfolio reallocation + crisis stress testing | M4 | Project Pattern |
| 21 | E2E Tier 4: Real-World User Scenarios | End-to-end user journeys: homepage discovery -> telemetry check -> matrix filter -> portfolio configuration -> article reading -> fund detail | M4 | Project Pattern |
| 22 | Final Milestone: 100% E2E Pass & Tier 5 Hardening | Pass 100% of Tiers 1-4 tests, white-box adversarial stress testing (Tier 5), fix any edge-case defects | M5 | Project Pattern |
| 23 | Independent Agent-as-Judge 8-Dimension Audit | Independent audit of typography, whitespace, hierarchy, color, motion, micro-interactions, responsive adaptability, originality | M5 | User Request R1 |
| 24 | Forensic Integrity Verification | Mandatory independent Forensic Auditor verification confirming authentic implementation, zero cheating, zero regressions | M5 | User Request |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Core Visual Foundation & Telemetry HUD | CSS tokens, typography, missing variables, keyframe collisions, dark/light theme, HUD telemetry visual styling, navigation | none | DONE |
| M2 | Interactive Quantitative Engines Polish | DOM ID fix, `#rank-table`, `#portfolio`, `#simulator`, `#radar`, range sliders, tabular nums, micro-interactions | M1 | DONE |
| M3 | Content Pages & SEO Pipeline Upgrade | `public/about.html`, `public/articles/*.html` (relative links, table wraps, takeaways), `scraper/generate_seo.py` footer/template refactor, clean 60-fund regeneration | M1 | PLANNED |
| M4 | Requirement-Driven E2E Test Suite (Tiers 1-4) | Multi-viewport test harness, Tiers 1-4 automated test suite, publish `TEST_READY.md` | none (parallel track) | DONE |
| M5 | Final Milestone: 100% E2E Pass, Tier 5 Hardening & Award Audit | Pass 100% E2E tests, Tier 5 adversarial coverage hardening, independent 8-dimension judge audit, forensic integrity audit | M2, M3, M4 | PLANNED |


## Interface Contracts
### Styling Tokens ↔ Quantitative Engines (`style.css` ↔ `index.html` & `app.js`)
- CSS custom properties must provide:
  - `--up`: positive tracking difference / gain (`#10b981` in dark, `#059669` in light)
  - `--down`: negative tracking difference / loss (`#ef4444` in dark, `#dc2626` in light)
  - `--bg`, `--card`, `--card-subtle`, `--border`, `--border-light`, `--txt`, `--txt2`, `--txt3`, `--accent`, `--accent-glow`
  - Dynamic classes added by `app.js` (`active`, `show`, `highlight`, `loading`, `is-selected`) must have distinct, polished styling rules.
- DOM ID Anchor Contract:
  - `index.html` must define `<section class="quota-bulletin-container" id="quota-bulletin-section">` (or dual ID aliasing) so `document.getElementById('quota-bulletin-section').scrollIntoView(...)` functions properly.

### Programmatic SEO Generator ↔ Design System (`generate_seo.py` ↔ `public/fund/*.html`)
- `generate_seo.py`'s `HTML_TEMPLATE` must output:
  - `<div class="footer-inner"><div class="footer-info">...</div><div class="footer-links">...</div></div>` instead of inline pipe-separated styles.
  - Linked stylesheet: `<link rel="stylesheet" href="/css/style.css?v=20261031_award">`.
  - Semantic container `<main class="container fund-detail-container">` with modern metric grid cards.
  - Execution command: `python scraper/generate_seo.py` must run cleanly and generate 60 fund pages with exit code 0.

### E2E Test Harness ↔ Application (`tests_e2e/` ↔ `public/`)
- Test runner executes multi-viewport assertions (375px, 768px, 1440px) against static files in `public/`.
- Validates:
  1. Python tests: `python -m unittest discover -s tests` (must pass 100%).
  2. JavaScript syntax: `node -c public/js/app.js public/js/sim-worker.js` (must pass with 0 errors).
  3. SEO generation: `python scraper/generate_seo.py` (must pass with 0 errors).
  4. Viewport layout: Zero horizontal scroll overflow (`scrollWidth <= clientWidth`) on 375px, 768px, 1440px across index, about, articles, and fund detail pages.
  5. Interactive components initialize without JS console errors.

## Code Layout
- `public/css/style.css`: All core styles, variables, reset, typography, components, animations, responsive queries.
- `public/index.html`: Main single-page application markup.
- `public/js/app.js`: Main application logic (DO NOT rename or break 159 IDs).
- `public/js/sim-worker.js`: Web worker for Monte Carlo calculations.
- `public/about.html`: About page.
- `public/articles/*.html`: Quantitative research articles (18 files).
- `public/articles/index.html`: Research reports hub.
- `scraper/generate_seo.py`: Programmatic SEO generator for fund detail pages.
- `public/fund/*.html`: 60 generated fund detail pages.
- `tests/`: Existing 94 Python unit tests.
- `tests_e2e/`: Requirement-driven E2E test suite.
