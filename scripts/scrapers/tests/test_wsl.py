from __future__ import annotations

from unittest.mock import patch

from scripts.scrapers.wsl import COMPETITION, WSL_URL, scrape_wsl, scrape_wsl_results

SAMPLE_MATCHES = [
    {
        "status": "UPCOMING",
        "matchDateLocal": "2026-09-26T12:30:00",
        "stadiumName": "Stamford Bridge",
        "editorial": {"broadcasters": {"broadcasterNational1": "BBC One|https://www.bbc.co.uk/"}},
        "home": {"officialName": "Chelsea"},
        "away": {"officialName": "Aston Villa"},
        "homeScorePush": None,
        "awayScorePush": None,
    },
    {
        "status": "FINISHED",
        "matchDateLocal": "2026-09-04T19:00:00",
        "stadiumName": "CopperJax Community Stadium",
        "editorial": {"broadcasters": {"broadcasterNational1": "Sky Sports|https://www.skysports.com/"}},
        "home": {"officialName": "London City Lionesses"},
        "away": {"officialName": "Manchester United"},
        "homeScorePush": 2,
        "awayScorePush": 1,
    },
]


def test_scrape_wsl_uses_the_wsl_competition_label_and_url():
    with patch("scripts.scrapers.wsl.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_wsl()

    mocked.assert_called_once_with(WSL_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["home_team"] == "Chelsea"


def test_scrape_wsl_results_uses_the_wsl_competition_label_and_url():
    with patch("scripts.scrapers.wsl.fetch_wslfootball_matches", return_value=SAMPLE_MATCHES) as mocked:
        df = scrape_wsl_results()

    mocked.assert_called_once_with(WSL_URL)
    assert len(df) == 1
    assert df.iloc[0]["competition"] == COMPETITION
    assert df.iloc[0]["home_score"] == 2
