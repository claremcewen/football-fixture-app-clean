from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.england_u20_women import parse_england_u20_lines


def test_parses_world_cup_and_friendly_with_clear_labels():
    df = parse_england_u20_lines(load_fixture("england_u20_women_sample.txt"))

    assert len(df) == 2

    world_cup = df.iloc[0]
    assert world_cup["competition"] == "England Women U20 - FIFA U20 Women's World Cup"
    assert world_cup["home_team"] == "Canada"
    assert world_cup["away_team"] == "England"
    assert world_cup["kickoff_uk"] == "2026-09-05 17:00"
    assert world_cup["venue"] == "Stadion Miejski"

    friendly = df.iloc[1]
    assert friendly["competition"] == "England Women U20 - Friendly"
    assert friendly["home_team"] == "England"
    assert friendly["away_team"] == "Netherlands"
    assert friendly["venue"] == "-"


def test_live_snapshot_parses_without_crashing():
    df = parse_england_u20_lines(load_fixture("england_u20_women_live.txt"))
    assert "home_team" in df.columns
    assert len(df) > 0
