from __future__ import annotations

from .common import fetch_wslfootball_matches, wslfootball_fixtures_df, wslfootball_results_df

WSL2_URL = "https://www.wslfootball.com/fixtures/wsl2"
COMPETITION = "Barclays WSL2"


def scrape_wsl2():
    matches = fetch_wslfootball_matches(WSL2_URL)
    return wslfootball_fixtures_df(matches, COMPETITION, WSL2_URL)


def scrape_wsl2_results():
    matches = fetch_wslfootball_matches(WSL2_URL)
    return wslfootball_results_df(matches, COMPETITION, WSL2_URL)
