from __future__ import annotations

from .common import fetch_lines, parse_wslfootball

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"


def scrape_wsl():
    lines = fetch_lines(WSL_URL)
    return parse_wsl_lines(lines)


def parse_wsl_lines(lines):
    return parse_wslfootball(lines, COMPETITION, WSL_URL)
