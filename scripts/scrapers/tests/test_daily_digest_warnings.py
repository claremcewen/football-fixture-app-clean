from __future__ import annotations

import json

from scripts import daily_digest


def _status(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def test_no_warning_when_every_source_is_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_digest, "FIXTURES_STATUS_FILE", _status(tmp_path, "f.json", {"WSL": {"ok": True, "rows": 5}}))
    monkeypatch.setattr(daily_digest, "RESULTS_STATUS_FILE", _status(tmp_path, "r.json", {"WSL": {"ok": True, "rows": 5}}))

    assert daily_digest.scraper_warnings() == []
    assert daily_digest.with_warnings("DIGEST", []) == "DIGEST"


def test_failed_sources_are_named_in_plain_english(tmp_path, monkeypatch):
    fixtures = {
        "FAWNL": {"ok": False, "rows": 472, "note": "scraper raised: 400 Client Error: Bad Request for url: https://x"},
        "WSL": {"ok": True, "rows": 150},
    }
    results = {
        "England Women": {"ok": False, "rows": 2, "note": "scraper returned 0 rows; fell back to previous data"},
        "UWCL": {"ok": False, "rows": 9, "note": "scraper returned 3 rows, a >50% drop from 20 previous; treated as a probable partial/broken scrape"},
    }
    monkeypatch.setattr(daily_digest, "FIXTURES_STATUS_FILE", _status(tmp_path, "f.json", fixtures))
    monkeypatch.setattr(daily_digest, "RESULTS_STATUS_FILE", _status(tmp_path, "r.json", results))

    warnings = daily_digest.scraper_warnings()
    assert warnings == [
        "- FAWNL fixtures: the update failed",
        "- England Women results: the source returned nothing",
        "- UWCL results: the source returned only partial data",
    ]
    text = daily_digest.with_warnings("DIGEST", warnings)
    assert text.startswith("!! DATA WARNING")
    assert "- FAWNL fixtures: the update failed" in text
    assert text.endswith("DIGEST")


def test_missing_or_unreadable_status_files_never_break_the_digest(tmp_path, monkeypatch):
    monkeypatch.setattr(daily_digest, "FIXTURES_STATUS_FILE", tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(daily_digest, "RESULTS_STATUS_FILE", bad)

    assert daily_digest.scraper_warnings() == []
