from __future__ import annotations

from .common import fetch_lines, parse_wslfootball

PLAYERS_CUP_URL = "https://www.wslfootball.com/fixtures/league-cup"
COMPETITION = "Subway Players Cup"


def scrape_players_cup():
    lines = fetch_lines(PLAYERS_CUP_URL)
    return parse_players_cup_lines(lines)


def parse_players_cup_lines(lines):
    return parse_wslfootball(lines, COMPETITION, PLAYERS_CUP_URL)
