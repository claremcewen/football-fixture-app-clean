from __future__ import annotations

from unittest.mock import patch

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.common import (
    fetch_wslfootball_matches,
    wslfootball_fixtures_df,
    wslfootball_results_df,
)


def _load_matches():
    html = (FIXTURES_DIR / "wslfootball_matches_sample.html").read_text(encoding="utf-8")
    with patch("scripts.scrapers.common.fetch_html", return_value=html):
        return fetch_wslfootball_matches("https://example.invalid/fixtures")


def test_extracts_every_embedded_match_object():
    matches = _load_matches()
    assert len(matches) == 2


def test_fixtures_df_only_keeps_upcoming_matches_with_broadcaster_and_venue():
    matches = _load_matches()
    df = wslfootball_fixtures_df(matches, "Barclays WSL", "https://example.invalid/fixtures")

    assert len(df) == 1
    row = df.iloc[0]
    assert row["home_team"] == "Chelsea"
    assert row["away_team"] == "Aston Villa"
    # matchDateLocal is already UK local time - used directly, no conversion.
    assert row["kickoff_uk"] == "2026-09-26 12:30"
    assert row["venue"] == "Stamford Bridge"
    # "Name|url" in the source - only the name is kept.
    assert row["watch_platforms"] == "BBC One"


def test_results_df_only_keeps_finished_matches_with_scores():
    matches = _load_matches()
    df = wslfootball_results_df(matches, "Barclays WSL", "https://example.invalid/fixtures")

    assert len(df) == 1
    row = df.iloc[0]
    assert row["home_team"] == "London City Lionesses"
    assert row["away_team"] == "Manchester United"
    assert row["home_score"] == 2
    assert row["away_score"] == 1
    assert row["kickoff_uk"] == "2026-09-04 19:00"


def test_live_footballontv_broadcasts_match_the_exact_competition_tag_only():
    import datetime

    from scripts.scrapers.common import parse_live_football_on_tv_broadcasts

    lines = [
        "Saturday 17th October 2026",
        "12:45",
        "Arsenal Women v Birmingham City Women",
        "Women's Super League",
        "Sky Sports Premier League",
        "Sky Sports Mix",
        "14:00",
        "Watford Women v Durham Women",
        "Women's Super League 2",
        "YouTube",
        "Sunday 18th October 2026",
    ]
    wsl = parse_live_football_on_tv_broadcasts(lines, "Women's Super League")
    assert wsl == {
        (datetime.date(2026, 10, 17), "arsenal", "birmingham city"): "Sky Sports Premier League, Sky Sports Mix"
    }
    wsl2 = parse_live_football_on_tv_broadcasts(lines, "Women's Super League 2")
    assert list(wsl2.values()) == ["YouTube"]


def test_blank_wslfootball_broadcaster_falls_back_to_live_footballontv():
    import datetime

    matches = _load_matches()
    fallback = {(datetime.date(2026, 9, 26), "chelsea", "aston villa"): "Sky Sports Mix"}
    # The sample's own broadcaster ("BBC One") wins when present...
    df = wslfootball_fixtures_df(matches, "Barclays WSL", "u", fallback)
    assert df.iloc[0]["watch_platforms"] == "BBC One"
    # ...and the fallback only fills a blank one.
    matches[1]["editorial"]["broadcasters"]["broadcasterNational1"] = ""
    df = wslfootball_fixtures_df(matches, "Barclays WSL", "u", fallback)
    assert df.iloc[0]["watch_platforms"] == "Sky Sports Mix"
