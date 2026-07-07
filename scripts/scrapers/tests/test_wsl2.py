from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.wsl2 import parse_wsl2_lines


def test_parses_populated_fixture_list():
    df = parse_wsl2_lines(load_fixture("wsl2_sample.txt"))

    assert len(df) == 1

    first = df.iloc[0]
    assert first["home_team"] == "Durham"
    assert first["away_team"] == "Sheffield United"
    assert first["kickoff_uk"] == "2026-09-12 12:00"
    assert first["venue"] == "Maiden Castle Sports Park"
    assert "YouTube" in first["watch_platforms"]


def test_live_snapshot_parses_without_crashing():
    df = parse_wsl2_lines(load_fixture("wsl2_live.txt"))
    assert "home_team" in df.columns
