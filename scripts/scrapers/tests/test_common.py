from __future__ import annotations

import datetime

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.common import parse_watch_platform_lookup_lines


def test_finds_matches_for_the_given_team_only():
    lines = load_fixture("live_football_on_tv_international_sample.txt")

    u20 = parse_watch_platform_lookup_lines(lines, "England Women U20")
    assert u20 == {datetime.date(2026, 9, 5): "DAZN"}

    senior = parse_watch_platform_lookup_lines(lines, "England Women")
    assert senior == {datetime.date(2026, 10, 9): "ITV TBC"}


def test_handles_a_tbc_kickoff_time_as_an_entry_boundary():
    # The Greece v England entry's own kickoff time is "TBC", not a real
    # HH:MM - still needs to be recognised as the start of the *next*
    # entry so the previous one's broadcaster-line collection stops there.
    lines = load_fixture("live_football_on_tv_international_sample.txt")
    lookup = parse_watch_platform_lookup_lines(lines, "England Women")
    assert lookup[datetime.date(2026, 10, 9)] == "ITV TBC"


def test_stops_at_page_footer_for_the_last_match_in_the_list():
    # "Wales Women v Albania Women" is the last match in the sample and is
    # immediately followed by footer content with no time/date line of its
    # own - the footer strings must not leak into its broadcaster list.
    lines = load_fixture("live_football_on_tv_international_sample.txt")
    lookup = parse_watch_platform_lookup_lines(lines, "Wales Women")
    assert lookup[datetime.date(2026, 11, 13)] == "BBC iPlayer, BBC Sport Website"


def test_multiple_broadcaster_lines_are_joined():
    lines = load_fixture("live_football_on_tv_international_sample.txt")
    lookup = parse_watch_platform_lookup_lines(lines, "England")
    assert lookup[datetime.date(2026, 11, 12)] == "ITV1, STV, ITVX, STV Player"
