from __future__ import annotations

from .common import fetch_wslfootball_matches, wslfootball_fixtures_df, wslfootball_results_df

PLAYERS_CUP_URL = "https://www.wslfootball.com/fixtures/league-cup"
COMPETITION = "Subway Players Cup"


def scrape_players_cup():
    matches = fetch_wslfootball_matches(PLAYERS_CUP_URL)
    return wslfootball_fixtures_df(matches, COMPETITION, PLAYERS_CUP_URL)


def scrape_players_cup_results():
    matches = fetch_wslfootball_matches(PLAYERS_CUP_URL)
    return wslfootball_results_df(matches, COMPETITION, PLAYERS_CUP_URL)
