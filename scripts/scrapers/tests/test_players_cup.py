from __future__ import annotations

from unittest.mock import patch

from scripts.scrapers.players_cup import (
    COMPETITION,
    PLAYERS_CUP_URL,
    scrape_players_cup,
    scrape_players_cup_results,
)

SAMPLE_MATCHES = [
    {
        "status": "UPCOMING",
        "matchDateLocal": "2026-09-30T19:00:00",
        "stadiumName": "Chigwell Construction Stadium",
        "editorial": {"broadcasters": {"broadcasterNational1": ""}},
        "home": {"officialName": "West Ham United"},
        "away": {"officialName": "Southampton"},
        "homeScorePush": None,
        "awayScorePush": None,
    },
    {
        "status": "FINISHED",
        "matchDateLocal": "2026-09-23T19:00:00",
        "stadiumName": "Chigwell Construction Stadium",
        "editorial": {"broadcasters": {"broadcasterNational1": ""}},
        "home": {"officialName": "Tottenham Hotspur"},
        "away": {"officialName": "West Ham United"},
        # A shootout-decided tie - full-time score stays 0-0, the shootout
        # result itself isn't captured (this app doesn't track penalties).
        "homeScorePush": 0,
        "awayScorePush": 0,
    },
]


def test_scrape_players_cup_uses_its_own_competition_label_and_url():
    with patch("scripts.scrapers.players_cup.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_players_cup()

    mocked.assert_called_once_with(PLAYERS_CUP_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["home_team"] == "West Ham United"


def test_scrape_players_cup_results_uses_its_own_competition_label_and_url():
    with patch("scripts.scrapers.players_cup.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_players_cup_results()

    mocked.assert_called_once_with(PLAYERS_CUP_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["home_team"] == "Tottenham Hotspur"
    assert df.iloc[0]["home_score"] == 0
    assert df.iloc[0]["away_score"] == 0
