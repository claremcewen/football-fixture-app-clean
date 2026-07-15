from __future__ import annotations

import json

from scripts.scrapers.tests.helpers import FIXTURES_DIR
from scripts.scrapers.fawnl import parse_fawnl_matches


def load_json_fixture(filename: str) -> dict:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_parses_populated_match_list():
    df = parse_fawnl_matches(load_json_fixture("fawnl_sample.json"))

    assert len(df) == 2

    first = df.iloc[0]
    assert first["home_team"] == "Wycombe Wanderers"
    assert first["away_team"] == "Torquay United"
    assert first["competition"] == "Division 1 South West"
    assert first["kickoff_uk"] == "2026-09-06 14:00"
    assert first["venue"] == "-"

    second = df.iloc[1]
    assert second["competition"] == "Northern Premier Division"


def test_live_snapshot_parses_without_crashing():
    df = parse_fawnl_matches(load_json_fixture("fawnl_live.json"))
    assert "home_team" in df.columns
    assert len(df) > 0
