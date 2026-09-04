from __future__ import annotations

import datetime

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
    # No watch_lookup passed at all - stays blank, same as before this was added.
    assert first["watch_platforms"] == ""

    second = df.iloc[1]
    assert second["home_team"] == "England"
    assert second["away_team"] == "Greece"


def test_applies_watch_platforms_from_the_lookup_by_date():
    # englandfootball.com itself has no broadcaster field - the kick-off
    # time being "TBC" on the source page doesn't mean the broadcaster is
    # unknown too; a real "ITV TBC" entry (channel confirmed, exact slot
    # not) cross-referenced from live-footballontv.com by date still comes
    # through.
    watch_lookup = {datetime.date(2026, 10, 9): "ITV TBC"}
    df = parse_england_lines(load_fixture("england_live.txt"), watch_lookup)

    assert df.iloc[0]["watch_platforms"] == "ITV TBC"
