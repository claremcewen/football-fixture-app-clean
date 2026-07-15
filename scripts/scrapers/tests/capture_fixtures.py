"""One-off helper to (re)capture saved sample input for scraper tests.

Run manually when you want to refresh what the tests are checked against:

    python -m scripts.scrapers.tests.capture_fixtures

This hits the live sites once and saves fetch_lines() output as text files
under tests/fixtures/, so the actual pytest suite never needs the network.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import requests

from scripts.scrapers.common import fetch_lines
from scripts.scrapers.fawnl import API_URL, DIVISION_COMPETITION_IDS, HEADERS
from scripts.scrapers.internationals import ENGLAND_URL
from scripts.scrapers.nwsl import NWSL_URL
from scripts.scrapers.uwcl import UWCL_URL
from scripts.scrapers.wsl import WSL_URL
from scripts.scrapers.wsl2 import WSL2_URL

FIXTURES_DIR = Path(__file__).parent / "fixtures"

SOURCES = {
    "wsl_live.txt": WSL_URL,
    "wsl2_live.txt": WSL2_URL,
    "england_live.txt": ENGLAND_URL,
    "uwcl_live.txt": UWCL_URL,
    "nwsl_live.txt": NWSL_URL,
}


def capture_fawnl() -> None:
    # FAWNL is a JSON API, not a fetch_lines() text page, so it's captured
    # separately - trimmed to a handful of items, since the full season is
    # ~800 fixtures and the live snapshot test only needs enough to confirm
    # parsing doesn't crash.
    print(f"Fetching {API_URL} ...")
    today = date.today()
    params = {
        "limit": 1000,
        "period": "Custom",
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=300)).isoformat(),
        "sort": "asc",
        "status": "fixture",
        "competition": ",".join(DIVISION_COMPETITION_IDS.values()),
    }
    response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    trimmed = {"pagination": data["pagination"], "items": data["items"][:20]}
    out_path = FIXTURES_DIR / "fawnl_live.json"
    out_path.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")
    print(f"  saved {len(trimmed['items'])} items to {out_path}")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in SOURCES.items():
        print(f"Fetching {url} ...")
        lines = fetch_lines(url)
        out_path = FIXTURES_DIR / filename
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  saved {len(lines)} lines to {out_path}")

    capture_fawnl()


if __name__ == "__main__":
    main()
