from __future__ import annotations

from .common import fetch_lines, parse_wslfootball

WSL2_URL = "https://www.wslfootball.com/fixtures/wsl2"
COMPETITION = "Barclays WSL2"


def scrape_wsl2():
    lines = fetch_lines(WSL2_URL)
    return parse_wsl2_lines(lines)


def parse_wsl2_lines(lines):
    return parse_wslfootball(lines, COMPETITION, WSL2_URL)
