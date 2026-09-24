from __future__ import annotations

from unittest.mock import patch

from scripts.scrapers.wsl2 import COMPETITION, WSL2_URL, scrape_wsl2, scrape_wsl2_results

SAMPLE_MATCHES = [
    {
        "status": "UPCOMING",
        "matchDateLocal": "2026-09-27T13:00:00",
        "stadiumName": "Vicarage Road",
        "editorial": {"broadcasters": {"broadcasterNational1": "YouTube|https://youtube.com/"}},
        "home": {"officialName": "Watford"},
        "away": {"officialName": "Burnley"},
        "homeScorePush": None,
        "awayScorePush": None,
    },
    {
        "status": "FINISHED",
        "matchDateLocal": "2026-09-06T12:00:00",
        "stadiumName": "Maiden Castle",
        "editorial": {"broadcasters": {"broadcasterNational1": "YouTube|https://youtube.com/"}},
        "home": {"officialName": "Durham"},
        "away": {"officialName": "Southampton"},
        "homeScorePush": 1,
        "awayScorePush": 3,
    },
]


def test_scrape_wsl2_uses_the_wsl2_competition_label_and_url():
    with patch("scripts.scrapers.wsl2.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_wsl2()

    mocked.assert_called_once_with(WSL2_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["home_team"] == "Watford"


def test_scrape_wsl2_results_uses_the_wsl2_competition_label_and_url():
    with patch("scripts.scrapers.wsl2.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_wsl2_results()

    mocked.assert_called_once_with(WSL2_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["away_score"] == 3
