from __future__ import annotations

from .common import fetch_html, fetch_lines, parse_wikipedia_results_grid, parse_wslfootball

WSL2_URL = "https://www.wslfootball.com/fixtures/wsl2"
COMPETITION = "Barclays WSL2"

# See wsl.py's WSL_RESULTS_URL comment - same situation, same fix.
WSL2_RESULTS_URL = "https://en.wikipedia.org/wiki/2026%E2%80%9327_Women%27s_Super_League_2"


def scrape_wsl2():
    lines = fetch_lines(WSL2_URL)
    return parse_wsl2_lines(lines)


def parse_wsl2_lines(lines):
    return parse_wslfootball(lines, COMPETITION, WSL2_URL)


def scrape_wsl2_grid_scores() -> list[dict]:
    html = fetch_html(WSL2_RESULTS_URL)
    return parse_wikipedia_results_grid(html)
