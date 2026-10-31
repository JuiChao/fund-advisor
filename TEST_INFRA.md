# E2E Test Infra: fund-advisor

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on internal implementation design.
- Derived directly from `ORIGINAL_REQUEST.md` and user-facing requirements.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing across 3 target viewports: Mobile (375px), Tablet (768px), and Desktop (1440px).

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Real-time US Eastern Time Telemetry HUD | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | 60-Target Quantitative Matrix Table (#rank-table) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | MPT Asset Allocation Portfolio Configurator (#portfolio) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | 5,000-Run Monte Carlo Wealth Simulator (#simulator) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Market Purchase Restriction Radar (#radar) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 6 | About Page Presentation (about.html) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 7 | Research Reports (18 articles) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 8 | 60 Individual Fund Detail Pages | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 9 | Python Unit Test Suite | ORIGINAL_REQUEST §Verification | 5 | 5 | ✓ |
| 10 | JavaScript Syntax & Runtime Integrity | ORIGINAL_REQUEST §Verification | 5 | 5 | ✓ |
| 11 | SEO Generation Pipeline | ORIGINAL_REQUEST §Verification | 5 | 5 | ✓ |
| 12 | Responsive Multi-Viewport Adaptability | ORIGINAL_REQUEST §R1, Acceptance | 5 | 5 | ✓ |

## Test Architecture
- Test runner: Python automated test runner script `tests_e2e/run_all_e2e.py` and Node validator scripts.
- Execution command: `python tests_e2e/run_all_e2e.py`
- Pass/fail semantics: All tests must exit with code 0 and zero failures/regressions.
- Directory layout:
  - `tests_e2e/tier1_feature_coverage/`
  - `tests_e2e/tier2_boundary_corner/`
  - `tests_e2e/tier3_pairwise_cross/`
  - `tests_e2e/tier4_real_world/`
  - `tests_e2e/run_all_e2e.py`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Global Asset Allocation User Flow | Telemetry HUD -> Ranking Table -> Portfolio Configurator -> Crisis Stress Tests | High |
| 2 | QDII Fund Selection & Quota Check Flow | Ranking Filter -> Purchase Radar -> Fund Detail Page Navigation | Medium |
| 3 | Retirement Wealth Accumulation Simulation | Monte Carlo Simulator -> DCA Slider Adjustments -> Probability Ladder Evaluation | High |
| 4 | Quantitative Research Due Diligence Flow | About Page -> Methodology -> Research Article -> In-text Data Table -> Fund Detail | Medium |
| 5 | Cross-Device Responsive Transition Flow | Mobile (375px) -> Tablet (768px) -> Desktop (1440px) viewport consistency without overflow | High |

## Coverage Thresholds
- Total identified feature areas: 12
- Tier 1: ≥5 per feature (≥60 test cases)
- Tier 2: ≥5 per feature (≥60 test cases)
- Tier 3: pairwise coverage of major feature interactions (≥15 test cases)
- Tier 4: ≥5 realistic application scenarios (≥5 test cases)
- Total target test cases: ≥140 test cases
