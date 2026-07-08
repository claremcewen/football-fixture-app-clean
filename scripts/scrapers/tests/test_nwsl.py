from __future__ import annotations

from scripts.scrapers.tests.helpers import load_fixture
from scripts.scrapers.nwsl import parse_nwsl_lines


def test_parses_populated_fixture_list():
    df = parse_nwsl_lines(load_fixture("nwsl_sample.txt"))

    assert len(df) == 4

    first = df.iloc[0]
    assert first["home_team"] == "Boston Legacy"
    assert first["away_team"] == "Chicago Stars"
    assert first["kickoff_uk"] == "2026-09-12 01:00"
    assert first["venue"] == "Gillette Stadium"
    assert "TNT Sports 2" in first["watch_platforms"]
    assert "HBO Max" in first["watch_platforms"]

    second = df.iloc[1]
    assert second["watch_platforms"] == "NWSL+"


def test_unmapped_home_team_falls_back_to_dash():
    lines = [
        "Saturday 12th September 2026",
        "01:00",
        "Some New Expansion Team v Chicago Stars",
        "NWSL",
        "NWSL+",
    ]
    df = parse_nwsl_lines(lines)
    assert df.iloc[0]["venue"] == "-"


def test_live_snapshot_parses_without_crashing():
    df = parse_nwsl_lines(load_fixture("nwsl_live.txt"))
    assert "home_team" in df.columns


def test_last_match_does_not_swallow_page_footer():
    # Regression: the last match in the scraped list is immediately
    # followed by footer/nav content, not another time/date line - without
    # a stop marker, all of that junk used to end up in its watch_platforms.
    lines = [
        "Saturday 12th September 2026",
        "22:00",
        "Washington Spirit v Chicago Stars",
        "NWSL",
        "NWSL+",
        "View Our Women's Football TV Schedule by Team",
        "Arsenal Women",
        "Back to Top",
        "About Us",
        "Privacy Policy",
    ]
    df = parse_nwsl_lines(lines)

    assert len(df) == 1
    assert df.iloc[0]["watch_platforms"] == "NWSL+"
