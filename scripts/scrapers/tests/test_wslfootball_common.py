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
