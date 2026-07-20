from __future__ import annotations

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.wafcon import parse_wafcon_matches


def load_html_fixture(filename: str) -> str:
    return FIXTURES_DIR.joinpath(filename).read_text(encoding="utf-8")


def test_parses_group_and_knockout_matches():
    df = parse_wafcon_matches(load_html_fixture("wafcon_sample.html"))

    assert len(df) == 3

    first = df.iloc[0]
    assert first["home_team"] == "Algeria"
    assert first["away_team"] == "Senegal"
    assert first["competition"] == "WAFCON 2026 - Group A"
    # 26 July 18:00 in Morocco (UTC+1) = 18:00 in the UK (BST, also UTC+1).
    assert first["kickoff_uk"] == "2026-07-26 18:00"
    assert first["venue"] == "Rabat Olympic Stadium, Rabat"

    final = df.iloc[-1]
    assert final["competition"] == "WAFCON 2026 - Final"
    assert final["home_team"] == "Winner SF1"
    assert final["away_team"] == "Winner SF2"


def test_live_snapshot_parses_without_crashing():
    df = parse_wafcon_matches(load_html_fixture("wafcon_live.html"))
    assert "home_team" in df.columns
    assert len(df) > 0
