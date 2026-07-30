from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.wsl import parse_wsl_lines


def test_parses_populated_fixture_list():
    df = parse_wsl_lines(load_fixture("wsl_sample.txt"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "London City Lionesses"
    assert first["away_team"] == "Manchester United"
    assert first["kickoff_uk"] == "2026-09-04 19:00"
    assert first["venue"] == "CopperJax Community Stadium"
    assert "Sky Sports" in first["watch_platforms"]

    second = df.iloc[1]
    assert second["home_team"] == "Chelsea"
    assert second["away_team"] == "Aston Villa"
    assert second["kickoff_uk"] == "2026-09-05 12:30"
    assert second["venue"] == "Stamford Bridge"
    assert "BBC One" in second["watch_platforms"]


def test_live_snapshot_parses_without_crashing():
    # Live site may legitimately show 0 upcoming fixtures (e.g. off-season,
    # only past results listed) - this just checks parsing doesn't error
    # and still returns the expected columns.
    df = parse_wsl_lines(load_fixture("wsl_live.txt"))
    assert "home_team" in df.columns
