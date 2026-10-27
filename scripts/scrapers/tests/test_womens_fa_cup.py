from __future__ import annotations

from scripts.scrapers.womens_fa_cup import _clean_team, parse_fixture_lines, parse_round_results


def test_club_names_are_stripped_back_to_the_short_form():
    assert _clean_team("Hashtag United FC Women") == "Hashtag United"
    assert _clean_team("Grimsby Town Women's FC") == "Grimsby Town"
    assert _clean_team("Thornaby FC Ladies") == "Thornaby"
    assert _clean_team("Bristol Rovers Women's") == "Bristol Rovers"
    assert _clean_team("Norton & Stockton Ancients LFC") == "Norton & Stockton Ancients"


def test_fixtures_keep_real_ties_and_skip_unresolved_ones():
    lines = [
        "Sunday 1 November 2026",
        "First Round Proper",
        "Kick Off", "No.", "Home", "Away",
        "14:00", "4", "Workington Town Women", "VS", "Mancunian Unity Women", "information",
        "Sunday 15 November 2026",
        "Second Round Proper",
        "Kick Off", "No.", "Home", "Away",
        "13:00", "3", "Loughborough Lightning Women", "VS", "Preston North End Women / i2i Women",
        "13:00", "1", "Chesterfield Women", "VS", "Leafield Athletic Ladies", "Live on TNT Sports 1",
    ]
    df = parse_fixture_lines(lines)

    assert len(df) == 2
    first = df.iloc[0]
    assert (first["home_team"], first["away_team"]) == ("Workington Town", "Mancunian Unity")
    assert first["kickoff_uk"] == "2026-11-01 14:00"
    assert first["competition"] == "Adobe Women's FA Cup - First Round Proper"
    # The unresolved "Team A / Team B" tie is skipped; the broadcaster note is kept.
    second = df.iloc[1]
    assert second["home_team"] == "Chesterfield"
    assert second["watch_platforms"] == "TNT Sports 1"


def test_results_keep_played_ties_and_skip_postponed_ones():
    lines = [
        "Sunday 25 October 2026",
        "Kick Off", "No.", "Home", "Away",
        "12:00", "39", "Exeter City Women FC", "2 - 0", "Hashtag United FC Women", "+", "Live on TNT Sports 1",
        "14:00", "4", "Workington Town Women FC", "P - P", "Mancunian Unity Women FC", "+", "Postponed",
        "14:00", "1", "Leeds Modernians Women FC", "1 - 3", "Liverpool Feds LFC", "+",
    ]
    df = parse_round_results(lines, "First Round Proper")

    assert len(df) == 2
    assert (df.iloc[0]["home_team"], df.iloc[0]["away_team"]) == ("Exeter City", "Hashtag United")
    assert (df.iloc[0]["home_score"], df.iloc[0]["away_score"]) == (2, 0)
    assert df.iloc[1]["kickoff_uk"] == "2026-10-25 14:00"
