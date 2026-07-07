"""One-off helper to (re)capture saved sample input for scraper tests.

Run manually when you want to refresh what the tests are checked against:

    python -m scripts.scrapers.tests.capture_fixtures

This hits the live sites once and saves fetch_lines() output as text files
under tests/fixtures/, so the actual pytest suite never needs the network.
"""

from __future__ import annotations

from pathlib import Path

from scripts.scrapers.common import fetch_lines
from scripts.scrapers.internationals import ENGLAND_URL
from scripts.scrapers.uwcl import UWCL_URL
from scripts.scrapers.wsl import WSL_URL
from scripts.scrapers.wsl2 import WSL2_URL

FIXTURES_DIR = Path(__file__).parent / "fixtures"

SOURCES = {
    "wsl_live.txt": WSL_URL,
    "wsl2_live.txt": WSL2_URL,
    "england_live.txt": ENGLAND_URL,
    "uwcl_live.txt": UWCL_URL,
}


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in SOURCES.items():
        print(f"Fetching {url} ...")
        lines = fetch_lines(url)
        out_path = FIXTURES_DIR / filename
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  saved {len(lines)} lines to {out_path}")


if __name__ == "__main__":
    main()
