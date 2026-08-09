from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.players_cup import parse_players_cup_lines


def test_parses_populated_fixture_list():
    df = parse_players_cup_lines(load_fixture("players_cup_sample.txt"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Tottenham Hotspur"
    assert first["away_team"] == "West Ham United"
    assert first["kickoff_uk"] == "2026-09-23 19:00"
    assert first["venue"] == "BetWright Stadium"

    second = df.iloc[1]
    assert second["home_team"] == "Crystal Palace"
    assert second["away_team"] == "Watford"
    assert second["venue"] == "VBS Community Stadium"


def test_live_snapshot_parses_without_crashing():
    df = parse_players_cup_lines(load_fixture("players_cup_live.txt"))
    assert "home_team" in df.columns
    assert len(df) > 0
