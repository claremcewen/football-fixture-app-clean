from __future__ import annotations

import datetime

from scripts.scrapers.world_cup_playoffs import parse_playoff_fixtures, parse_playoff_results


def _box(home, away, score, date, time):
    return (
        '<div class="footballbox">'
        f'<div class="fleft"><div class="fdate"><span class="bday">{date}</span></div>'
        f'<div class="ftime">{time}</div></div>'
        f'<table class="fevent"><tr><th class="fhome"><span itemprop="name">{home}</span></th>'
        f'<th class="fscore">{score}</th>'
        f'<th class="faway"><span itemprop="name">{away}</span></th></tr></table></div>'
    )


HTML = (
    _box("Albania", "Wales", "v", "2026-10-09", "18:00")
    + _box("Greece", "England", "v", "2026-10-09", "18:30")  # England's ties come from elsewhere
    + _box("Lithuania", "Sweden", "2–1", "2026-10-09", "18:05 (19:05 UTC+3)")
    + _box("Winner Tie 11", "Winner Tie 3", "v", "2026-11", "")  # second round, not yet real
)


def test_fixtures_keep_unplayed_non_england_ties_with_uk_time_and_broadcaster():
    lookup = {(datetime.date(2026, 10, 9), "albania", "wales"): "BBC Two Wales"}
    df = parse_playoff_fixtures(HTML, lookup)

    assert len(df) == 1
    row = df.iloc[0]
    assert (row["home_team"], row["away_team"]) == ("Albania", "Wales")
    # UEFA's listed 18:00 (CEST) is 17:00 UK time.
    assert row["kickoff_uk"] == "2026-10-09 17:00"
    assert row["watch_platforms"] == "BBC Two Wales"


def test_results_keep_only_played_ties():
    df = parse_playoff_results(HTML)

    assert len(df) == 1
    row = df.iloc[0]
    assert (row["home_team"], row["away_team"]) == ("Lithuania", "Sweden")
    assert (row["home_score"], row["away_score"]) == (2, 1)
