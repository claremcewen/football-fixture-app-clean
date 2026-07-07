from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.internationals import parse_england_lines


def test_parses_live_snapshot_fixtures_only():
    # England's fixture page mixes upcoming "Fixture" rows with past
    # "Results" rows in the same list - this checks that only the
    # upcoming ones get parsed out, using an actual saved page capture.
    df = parse_england_lines(load_fixture("england_live.txt"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Greece"
    assert first["away_team"] == "England"
    assert first["kickoff_uk"] == "2026-10-09 12:00"
    assert first["watch_notes"] == "Kick-off time to be confirmed"

    second = df.iloc[1]
    assert second["home_team"] == "England"
    assert second["away_team"] == "Greece"
