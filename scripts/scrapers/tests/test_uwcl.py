from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.uwcl import parse_uwcl_lines


def test_parses_populated_fixture_list():
    df = parse_uwcl_lines(load_fixture("uwcl_sample.txt"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Arsenal Women"
    assert first["away_team"] == "Bayern Munich Women"
    assert first["kickoff_uk"] == "2026-10-07 18:45"
    assert "Women's Champions League" in first["competition"]
    assert "BBC Two" in first["watch_platforms"]


def test_live_snapshot_parses_without_crashing():
    df = parse_uwcl_lines(load_fixture("uwcl_live.txt"))
    assert "home_team" in df.columns
