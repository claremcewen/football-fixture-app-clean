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


def test_fetches_every_page_and_never_asks_for_more_than_100_at_a_time():
    from unittest.mock import MagicMock, patch

    from scripts.scrapers.fawnl import PAGE_SIZE, _fetch_all_matches

    pages = {
        1: {"items": [{"id": "a"}, {"id": "b"}], "pagination": {"hasNextPage": True}},
        2: {"items": [{"id": "c"}], "pagination": {"hasNextPage": False}},
    }
    seen_params = []

    def fake_get(url, headers=None, params=None, timeout=None):
        seen_params.append(params)
        response = MagicMock()
        response.json.return_value = pages[params["page"]]
        return response

    with patch("scripts.scrapers.fawnl.requests.get", side_effect=fake_get):
        data = _fetch_all_matches({"status": "result"})

    assert [m["id"] for m in data["items"]] == ["a", "b", "c"]
    assert [p["page"] for p in seen_params] == [1, 2]
    # The API rejects anything over 100 with a 400 - the cause of weeks of
    # silently stale FAWNL data.
    assert all(p["limit"] == PAGE_SIZE <= 100 for p in seen_params)
