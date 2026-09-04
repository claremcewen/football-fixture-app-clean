from __future__ import annotations

import json

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.adran_premier import parse_adran_premier_matches


def load_json_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_parses_populated_match_list():
    df = parse_adran_premier_matches(load_json_fixture("adran_premier_sample.json"))

    assert len(df) == 3

    first = df.iloc[0]
    assert first["home_team"] == "Barry Town Utd"
    assert first["away_team"] == "Briton Ferry Llansawel"
    # 1788699600000ms is 2026-09-06 13:00 UTC, which is 14:00 in BST.
    assert first["kickoff_uk"] == "2026-09-06 14:00"
    assert first["competition"] == "Adran Premier"
    assert first["venue"] == "-"

    # "Women's FC" (a two-part suffix) and "WFC" both get stripped, matching
    # the FAW's own site's own name-cleaning behaviour.
    second = df.iloc[1]
    assert second["home_team"] == "Wrexham"
    assert second["away_team"] == "Aberystwyth Town"

    third = df.iloc[2]
    assert third["home_team"] == "Cardiff Met"
    assert third["away_team"] == "The New Saints"


def test_live_snapshot_parses_without_crashing():
    df = parse_adran_premier_matches(load_json_fixture("adran_premier_live.json"))
    assert "home_team" in df.columns
    assert len(df) == 56
    # None of the real team names should still carry the site's own
    # disambiguating suffixes once cleaned.
    for col in ("home_team", "away_team"):
        assert not df[col].str.contains("Women", case=False).any()
        assert not df[col].str.contains(r"\bFC\b", case=False, regex=True).any()
