from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.wsl2 import parse_wsl2_lines


def test_parses_populated_fixture_list():
    df = parse_wsl2_lines(load_fixture("wsl2_sample.txt"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Watford"
    assert first["away_team"] == "Burnley"
    assert first["kickoff_uk"] == "2026-09-04 19:30"
    assert first["venue"] == "Vicarage Road"
    assert "YouTube" in first["watch_platforms"]

    second = df.iloc[1]
    assert second["home_team"] == "Durham"
    assert second["away_team"] == "Southampton"
    assert second["kickoff_uk"] == "2026-09-06 12:00"
    assert second["venue"] == "Maiden Castle"
    assert "YouTube" in second["watch_platforms"]


def test_live_snapshot_parses_without_crashing():
    df = parse_wsl2_lines(load_fixture("wsl2_live.txt"))
    assert "home_team" in df.columns
