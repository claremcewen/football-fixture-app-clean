from __future__ import annotations

from .common import fetch_wslfootball_matches, wslfootball_fixtures_df, wslfootball_results_df

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"


def scrape_wsl():
    matches = fetch_wslfootball_matches(WSL_URL)
    return wslfootball_fixtures_df(matches, COMPETITION, WSL_URL)


def scrape_wsl_results():
    matches = fetch_wslfootball_matches(WSL_URL)
    return wslfootball_results_df(matches, COMPETITION, WSL_URL)
