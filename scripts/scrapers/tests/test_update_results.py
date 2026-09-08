from __future__ import annotations

import json

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.swpl import parse_swpl_results
from scripts.scrapers.fawnl import parse_fawnl_results
from scripts.scrapers.adran_premier import parse_adran_premier_result
from scripts.scrapers.internationals import parse_england_results_lines
from scripts.scrapers.england_u20_women import parse_england_u20_results_lines
from scripts.scrapers.uwcl import _parse_uwcl_results_html
from scripts.scrapers.common import parse_wikipedia_results_grid
from scripts.update_results import resolve_grid_scores
from scripts.scrapers.tests.helpers import FIXTURES_DIR, load_fixture


def load_json_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_swpl_results_only_keeps_played_matches_with_scores():
    df = parse_swpl_results(load_json_fixture("swpl_results_sample.json"))

    # The second match is still a "Fixture" (not yet played) - excluded.
    assert len(df) == 1

    row = df.iloc[0]
    assert row["home_team"] == "Glasgow City"
    assert row["away_team"] == "Celtic"
    assert row["home_score"] == 1
    assert row["away_score"] == 2
    assert row["kickoff_uk"] == "2026-08-16 16:10"


def test_fawnl_results_only_keeps_full_time_matches_with_scores():
    df = parse_fawnl_results(load_json_fixture("fawnl_results_sample.json"))

    # The postponed match has status != "FullTime" - excluded.
    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Rugby Borough"
    assert first["away_team"] == "Norwich City"
    assert first["competition"] == "Northern Premier Division"
    assert first["home_score"] == 1
    assert first["away_score"] == 0

    second = df.iloc[1]
    assert second["competition"] == "The FA WNL Cup"
    assert second["home_score"] == 5
    assert second["away_score"] == 0


def test_adran_premier_result_parses_a_played_match():
    match = parse_adran_premier_result(load_json_fixture("adran_premier_result_sample.json"))

    assert match is not None
    # Name-cleaning suffixes ("Women FC") get stripped, same as the fixtures parser.
    assert match["home_team"] == "Swansea City"
    assert match["away_team"] == "Cardiff City"
    assert match["home_score"] == 3
    assert match["away_score"] == 1
    assert match["kickoff_uk"] == "2026-09-06 17:15"


def test_adran_premier_result_returns_none_for_an_unplayed_match():
    unplayed = {**load_json_fixture("adran_premier_result_sample.json"), "liveStatus": "SCHEDULED"}
    assert parse_adran_premier_result(unplayed) is None


def test_england_women_results_parses_the_archive_with_scores():
    df = parse_england_results_lines(load_fixture("england_results_sample.txt"))

    assert len(df) == 3

    first = df.iloc[0]
    assert first["home_team"] == "England"
    assert first["away_team"] == "Ukraine"
    assert first["home_score"] == 3
    assert first["away_score"] == 0
    assert first["kickoff_uk"] == "2026-06-09 20:00"
    assert first["competition"] == "England Women - FIFA 2027 World Cup European Qualifiers"

    # An away game - team order in the score line follows the site's own
    # home-first display, not England-first.
    second = df.iloc[1]
    assert second["home_team"] == "Spain"
    assert second["away_team"] == "England"
    assert second["home_score"] == 4
    assert second["away_score"] == 0

    # A penalty-shootout ("AET") result still parses on the fixed-offset
    # score lines regardless of what trailing status text follows.
    third = df.iloc[2]
    assert third["home_team"] == "England"
    assert third["away_team"] == "Spain"
    assert third["home_score"] == 1
    assert third["away_score"] == 1
    assert third["kickoff_uk"] == "2025-07-27 17:00"


def test_uwcl_results_keeps_only_the_played_match():
    # The saved sample has one played match (score "0-0 (a.e.t.)") and one
    # still-upcoming fixture ("v" in place of a score) - the date is
    # rewritten to "recent" at test time (rather than trusting the sample's
    # own real capture date) so this doesn't age out of the scraper's own
    # results window as real time passes, the same trap that bit
    # test_england_u20_women.py's fixed sample date.
    import datetime

    html = (FIXTURES_DIR / "uwcl_results_sample.html").read_text(encoding="utf-8")
    recent_date = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    html = html.replace("2026-07-22", recent_date)

    rows = _parse_uwcl_results_html(html, "https://en.wikipedia.org/wiki/test")

    assert len(rows) == 1
    row = rows[0]
    assert row["home_team"] == "Neftçi"
    assert row["away_team"] == "Budućnost Podgorica"
    assert row["home_score"] == 0
    assert row["away_score"] == 0
    assert row["competition"] == "UEFA Women's Champions League"


def test_wikipedia_results_grid_only_returns_played_matches():
    html = (FIXTURES_DIR / "wsl_results_grid_sample.html").read_text(encoding="utf-8")
    scores = parse_wikipedia_results_grid(html)

    # 7 real played matches were in this snapshot when captured - everything
    # else in the 14x14 grid is still a future date, not a score.
    assert len(scores) == 7
    for entry in scores:
        assert entry["home_team"] != entry["away_team"]
        assert isinstance(entry["home_score"], int)
        assert isinstance(entry["away_score"], int)

    # Spot-check one specific real result from the snapshot.
    tottenham_west_ham = next(
        s for s in scores if s["home_team"] == "Tottenham Hotspur" and s["away_team"] == "West Ham United"
    )
    assert tottenham_west_ham["home_score"] == 3
    assert tottenham_west_ham["away_score"] == 1


def test_resolve_grid_scores_pairs_a_score_with_its_known_date():
    grid_scores = [
        {"home_team": "Arsenal", "away_team": "Chelsea", "home_score": 2, "away_score": 1},
        {"home_team": "Unknown FC", "away_team": "Mystery United", "home_score": 0, "away_score": 0},
    ]
    date_lookup = {("WSL", "Arsenal", "Chelsea"): "2026-09-13 14:00"}

    df, skipped = resolve_grid_scores(grid_scores, "Barclays WSL", "WSL", "https://en.wikipedia.org/wiki/test", date_lookup)

    # The second match has no known date in the lookup - skipped, not guessed.
    assert skipped == 1
    assert len(df) == 1

    row = df.iloc[0]
    assert row["home_team"] == "Arsenal"
    assert row["away_team"] == "Chelsea"
    assert row["kickoff_uk"] == "2026-09-13 14:00"
    assert row["home_score"] == 2
    assert row["away_score"] == 1


def test_england_u20_results_labels_world_cup_vs_friendly():
    df = parse_england_u20_results_lines(load_fixture("england_u20_women_results_sample.txt"))

    assert len(df) == 2

    world_cup = df.iloc[0]
    assert world_cup["competition"] == "England Women U20 - FIFA U20 Women's World Cup"
    assert world_cup["home_team"] == "Canada"
    assert world_cup["away_team"] == "England"
    assert world_cup["home_score"] == 1
    assert world_cup["away_score"] == 1
    assert world_cup["venue"] == "Stadion Miejski"

    friendly = df.iloc[1]
    assert friendly["competition"] == "England Women U20 - Friendly"
    assert friendly["home_score"] == 11
    assert friendly["away_score"] == 0
