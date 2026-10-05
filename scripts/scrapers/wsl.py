from __future__ import annotations

from .common import (
    build_live_football_on_tv_broadcast_lookup,
    fetch_wslfootball_matches,
    wslfootball_fixtures_df,
    wslfootball_results_df,
)

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"
LIVE_FOOTBALL_ON_TV_TAG = "Women's Super League"


def scrape_wsl():
    matches = fetch_wslfootball_matches(WSL_URL)
    broadcast_fallback = build_live_football_on_tv_broadcast_lookup(LIVE_FOOTBALL_ON_TV_TAG)
    return wslfootball_fixtures_df(matches, COMPETITION, WSL_URL, broadcast_fallback)


def scrape_wsl_results():
    matches = fetch_wslfootball_matches(WSL_URL)
    return wslfootball_results_df(matches, COMPETITION, WSL_URL)
