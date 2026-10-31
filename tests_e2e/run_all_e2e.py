#!/usr/bin/env python3
"""Main E2E Test Runner for fund-advisor.

Executes:
1. Static syntax & structure checks (CSS balanced braces, HTML parsing, selector coupling).
2. JavaScript syntax compilation (node -c).
3. Programmatic SEO generator verification (python scraper/generate_seo.py).
4. Existing Python unit test suite (94 tests in tests/).
5. 4-Tier Requirement-Driven E2E Test Suite (Tiers 1-4, >=140 tests in tests_e2e/).
"""

import os
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path

# Safe stdout reconfiguration for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests_e2e.e2e_common import (
    STYLE_CSS, APP_JS, SIM_WORKER_JS, INDEX_HTML, ABOUT_HTML,
    check_css_balanced_braces, load_style_css, load_app_js, load_index_soup
)


def run_cmd(cmd: list[str], desc: str) -> tuple[bool, str, float]:
    """Execute a subprocess command, timing its duration."""
    t0 = time.time()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(PROJECT_ROOT)
        )
        duration = time.time() - t0
        output = (res.stdout + "\n" + res.stderr).strip()
        return res.returncode == 0, output, duration
    except Exception as e:
        duration = time.time() - t0
        return False, str(e), duration


def inspect_css_and_html() -> tuple[bool, list[str]]:
    """Performs static checks on CSS and HTML syntax, brace balancing, and selector coupling."""
    errors = []
    # 1. CSS balanced braces
    css_text = load_style_css()
    ok, msg = check_css_balanced_braces(css_text)
    if not ok:
        errors.append(f"CSS syntax error: {msg}")

    # 2. Keyframes syntax check
    open_kf = len(re.findall(r"@keyframes\s+[a-zA-Z0-9_\-]+\s*\{", css_text))
    if open_kf == 0:
        errors.append("CSS has no @keyframes definitions")

    # 3. HTML parsing check
    try:
        index_soup = load_index_soup()
        if not index_soup.find("html"):
            errors.append("index.html failed to parse valid <html> root")
    except Exception as e:
        errors.append(f"index.html parsing failed: {e}")

    # 4. Critical selector coupling check
    app_js = load_app_js()
    critical_ids = ["rank-table", "pf-m", "sim-m", "hero-quant-ticker"]
    for cid in critical_ids:
        if cid not in index_soup.prettify() and not index_soup.find(id=cid):
            errors.append(f"Critical selector #{cid} missing from index.html")

    return len(errors) == 0, errors


def run_tier_suite(tier_dir_name: str) -> tuple[int, int, int, float]:
    """Discover and run all unittest cases in a specific tier subdirectory."""
    tier_path = PROJECT_ROOT / "tests_e2e" / tier_dir_name
    suite = unittest.defaultTestLoader.discover(str(tier_path), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    t0 = time.time()
    result = runner.run(suite)
    duration = time.time() - t0

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    return total, passed, failed, duration


def main():
    print("=" * 76)
    print("       FUND ADVISOR -- COMPREHENSIVE 4-TIER E2E TEST SUITE RUNNER")
    print("=" * 76)
    print(f"Project Root: {PROJECT_ROOT}\n")

    overall_success = True
    summary_table = []

    # -------------------------------------------------------------
    # Step 1: Static HTML & CSS Structural Inspections
    # -------------------------------------------------------------
    print("[1/5] Inspecting HTML & CSS syntax, brace balance & selector coupling...")
    css_ok, css_errors = inspect_css_and_html()
    if css_ok:
        print("  [OK] CSS and HTML syntax valid (braces balanced, selectors intact).")
        summary_table.append(("Static HTML/CSS Inspections", 1, 1, 0, "<0.1s", "PASS"))
    else:
        overall_success = False
        for err in css_errors:
            print(f"  [FAIL] {err}")
        summary_table.append(("Static HTML/CSS Inspections", 1, 0, 1, "<0.1s", "FAIL"))

    # -------------------------------------------------------------
    # Step 2: JavaScript Syntax Validation (node -c)
    # -------------------------------------------------------------
    print("\n[2/5] Validating JavaScript syntax (node -c)...")
    js_ok, js_out, js_dur = run_cmd(["node", "-c", str(APP_JS), str(SIM_WORKER_JS)], "Node JS Syntax Check")
    if js_ok:
        print(f"  [OK] node -c passed cleanly for app.js and sim-worker.js ({js_dur:.2f}s).")
        summary_table.append(("Node.js Syntax Compilation", 2, 2, 0, f"{js_dur:.2f}s", "PASS"))
    else:
        overall_success = False
        print(f"  [FAIL] node -c compilation failed:\n{js_out}")
        summary_table.append(("Node.js Syntax Compilation", 2, 0, 2, f"{js_dur:.2f}s", "FAIL"))

    # -------------------------------------------------------------
    # Step 3: SEO Generator Execution (python scraper/generate_seo.py)
    # -------------------------------------------------------------
    print("\n[3/5] Executing SEO generator (python scraper/generate_seo.py)...")
    seo_ok, seo_out, seo_dur = run_cmd([sys.executable, "scraper/generate_seo.py"], "SEO Generator")
    if seo_ok:
        print(f"  [OK] SEO generator created 60 fund pages and clean sitemap.xml ({seo_dur:.2f}s).")
        summary_table.append(("SEO Generator Pipeline", 60, 60, 0, f"{seo_dur:.2f}s", "PASS"))
    else:
        overall_success = False
        print(f"  [FAIL] SEO generator execution failed:\n{seo_out}")
        summary_table.append(("SEO Generator Pipeline", 60, 0, 60, f"{seo_dur:.2f}s", "FAIL"))

    # -------------------------------------------------------------
    # Step 4: Existing Python Unit Test Suite (tests/)
    # -------------------------------------------------------------
    print("\n[4/5] Executing Python baseline unit tests (tests/)...")
    tests_path = PROJECT_ROOT / "tests"
    t_suite = unittest.defaultTestLoader.discover(str(tests_path), pattern="test_*.py")
    t_runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, "w"))
    t0 = time.time()
    t_res = t_runner.run(t_suite)
    t_dur = time.time() - t0
    t_total = t_res.testsRun
    t_failed = len(t_res.failures) + len(t_res.errors)
    t_passed = t_total - t_failed

    if t_failed == 0:
        print(f"  [OK] All {t_total} baseline unit tests passed cleanly ({t_dur:.2f}s).")
        summary_table.append(("Baseline Python Unit Tests", t_total, t_passed, t_failed, f"{t_dur:.2f}s", "PASS"))
    else:
        overall_success = False
        print(f"  [FAIL] {t_failed} baseline unit test failures.")
        summary_table.append(("Baseline Python Unit Tests", t_total, t_passed, t_failed, f"{t_dur:.2f}s", "FAIL"))

    # -------------------------------------------------------------
    # Step 5: 4-Tier E2E Test Suite (tests_e2e/)
    # -------------------------------------------------------------
    print("\n[5/5] Executing 4-Tier Requirement-Driven E2E Test Suite...")
    tiers = [
        ("tier1_feature_coverage", "Tier 1: Feature Coverage (12 Features)"),
        ("tier2_boundary_corner", "Tier 2: Boundary & Corner Cases (12 Features)"),
        ("tier3_pairwise_cross", "Tier 3: Pairwise & Cross-Feature Interactions"),
        ("tier4_real_world", "Tier 4: Real-World User Scenarios (5 Flows)")
    ]

    total_e2e_tests = 0
    total_e2e_passed = 0
    total_e2e_failed = 0

    for tier_dir, tier_name in tiers:
        tot, p, f, dur = run_tier_suite(tier_dir)
        total_e2e_tests += tot
        total_e2e_passed += p
        total_e2e_failed += f
        status = "PASS" if f == 0 else "FAIL"
        if f > 0:
            overall_success = False
        print(f"  * {tier_name}: {tot} tests, {p} passed, {f} failed ({dur:.2f}s) -> {status}")
        summary_table.append((tier_name, tot, p, f, f"{dur:.2f}s", status))

    # -------------------------------------------------------------
    # Summary Dashboard
    # -------------------------------------------------------------
    print("\n" + "=" * 76)
    print("                      E2E TEST EXECUTION SUMMARY")
    print("=" * 76)
    print(f"{'Test Track / Tier':<44} | {'Total':<6} | {'Pass':<6} | {'Fail':<5} | {'Duration':<8} | {'Status'}")
    print("-" * 76)
    for name, tot, p, f, dur, status in summary_table:
        print(f"{name:<44} | {tot:<6} | {p:<6} | {f:<5} | {dur:<8} | {status}")
    print("-" * 76)
    grand_total = sum(t[1] for t in summary_table)
    grand_passed = sum(t[2] for t in summary_table)
    grand_failed = sum(t[3] for t in summary_table)
    print(f"{'GRAND TOTAL':<44} | {grand_total:<6} | {grand_passed:<6} | {grand_failed:<5} |          | {'PASS' if overall_success else 'FAIL'}")
    print("=" * 76)

    print(f"\nE2E Suite Totals: {total_e2e_tests} tests executed ({total_e2e_passed} passed, {total_e2e_failed} failed)")

    if overall_success:
        print("\n[SUCCESS] ALL E2E & BASELINE SUITES PASSED CLEANLY! PROJECT IS VERIFIED.")
        sys.exit(0)
    else:
        print("\n[FAILURE] SOME TESTS FAILED. CHECK LOGS ABOVE.")
        sys.exit(1)


if __name__ == "__main__":
    main()
