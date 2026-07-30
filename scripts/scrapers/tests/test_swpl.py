from __future__ import annotations

import json

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.swpl import parse_swpl_matches


def load_json_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_parses_populated_match_list():
    df = parse_swpl_matches(load_json_fixture("swpl_sample.json"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Spartans"
    assert first["away_team"] == "Rangers"
    assert first["kickoff_uk"] == "2027-02-21 14:00"
    assert first["venue"] == "The Vanloq Community Stadium"

    second = df.iloc[1]
    assert second["home_team"] == "Motherwell"
    assert second["away_team"] == "Montrose"


def test_live_snapshot_parses_without_crashing():
    df = parse_swpl_matches(load_json_fixture("swpl_live.json"))
    assert "home_team" in df.columns
    assert len(df) > 0
