"""Common test utilities, paths, and caching for E2E test suite."""
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = PROJECT_ROOT / "public"
INDEX_HTML = PUBLIC_DIR / "index.html"
ABOUT_HTML = PUBLIC_DIR / "about.html"
STYLE_CSS = PUBLIC_DIR / "css" / "style.css"
APP_JS = PUBLIC_DIR / "js" / "app.js"
SIM_WORKER_JS = PUBLIC_DIR / "js" / "sim-worker.js"
FUNDS_JSON = PUBLIC_DIR / "data" / "funds.json"
ALGO_JSON = PUBLIC_DIR / "data" / "algorithm.json"
LIMIT_CHANGES_JSON = PUBLIC_DIR / "data" / "limit_changes.json"
SIMULATIONS_JSON = PUBLIC_DIR / "data" / "simulations.json"
ARTICLES_DIR = PUBLIC_DIR / "articles"
FUND_PAGES_DIR = PUBLIC_DIR / "fund"
SITEMAP_XML = PUBLIC_DIR / "sitemap.xml"
ROBOTS_TXT = PUBLIC_DIR / "robots.txt"
SCRAPER_SEO_PY = PROJECT_ROOT / "scraper" / "generate_seo.py"
TESTS_DIR = PROJECT_ROOT / "tests"


@lru_cache(maxsize=1)
def load_index_soup() -> BeautifulSoup:
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@lru_cache(maxsize=1)
def load_about_soup() -> BeautifulSoup:
    with open(ABOUT_HTML, "r", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@lru_cache(maxsize=1)
def load_style_css() -> str:
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=1)
def load_app_js() -> str:
    with open(APP_JS, "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=1)
def load_funds_data() -> list:
    with open(FUNDS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_algo_data() -> dict:
    with open(ALGO_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_limit_changes_data() -> dict:
    with open(LIMIT_CHANGES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def get_article_files() -> list:
    return sorted([
        p for p in ARTICLES_DIR.glob("*.html")
        if p.name != "index.html"
    ])


def get_fund_page_files() -> list:
    return sorted(FUND_PAGES_DIR.glob("*.html"))


def check_css_balanced_braces(css_text: str) -> tuple[bool, str]:
    """Check that CSS curly braces and comments are balanced."""
    # Strip comments first
    stripped = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    # Check open/close braces
    open_count = stripped.count("{")
    close_count = stripped.count("}")
    if open_count != close_count:
        return False, f"Mismatched braces: {open_count} open vs {close_count} close"
    return True, "Balanced"
