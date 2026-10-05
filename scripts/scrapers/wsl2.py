from __future__ import annotations

from .common import (
    build_live_football_on_tv_broadcast_lookup,
    fetch_wslfootball_matches,
    wslfootball_fixtures_df,
    wslfootball_results_df,
)

WSL2_URL = "https://www.wslfootball.com/fixtures/wsl2"
COMPETITION = "Barclays WSL2"
LIVE_FOOTBALL_ON_TV_TAG = "Women's Super League 2"


def scrape_wsl2():
    matches = fetch_wslfootball_matches(WSL2_URL)
    broadcast_fallback = build_live_football_on_tv_broadcast_lookup(LIVE_FOOTBALL_ON_TV_TAG)
    return wslfootball_fixtures_df(matches, COMPETITION, WSL2_URL, broadcast_fallback)


def scrape_wsl2_results():
    matches = fetch_wslfootball_matches(WSL2_URL)
    return wslfootball_results_df(matches, COMPETITION, WSL2_URL)
