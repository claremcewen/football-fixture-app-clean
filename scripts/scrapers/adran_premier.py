from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from .common import build_df, build_results_df

# The FAW's own sites (faw.cymru) index every fixture across every one of
# their leagues into a public Typesense search collection - found via the
# "hopp_typesense_vars" JS config embedded in the fixtures page, which also
# exposes this search-only API key. Genuinely clean structured data (no
# HTML/text parsing), and unlike a single competition's own API, filtering
# by "theme" (season-independent) rather than the competition name (which
# changes wording/year every season, e.g. "Genero Adran Premier 26/27")
# means this doesn't need updating when a new season starts.
SEARCH_URL = "https://search.faw.cymru/collections/hp_faw_match_h/documents/search"
API_KEY = "F4rlR6OEla5R7naLjFsRUCpSDYz3sIih"
THEME = "Adran Premier"
FIXTURES_PAGE_URL = "https://faw.cymru/adran-leagues/adran-premier/fixtures-and-results/"
COMPETITION = "Adran Premier"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WomensFootballWatchGuide/1.0)",
    "X-TYPESENSE-API-KEY": API_KEY,
}

# The Typesense search index (used for fixtures above) has no score fields
# at all - final scores live on a separate API, keyed by this same search
# result's comet_id, run by a different vendor (analyticom) behind the
# scenes for the FAW's live match-centre widget. Not documented/versioned,
# same trade-off as the other API-backed sources here.
RESULTS_URL = "https://api-faw.analyticom.de/api/live/match/{comet_id}"
RESULTS_API_KEY = "ME8w7FdYVJQQJZJp7QwaDy8MRdrspAVqDcrxBeJ3"
RESULTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WomensFootballWatchGuide/1.0)",
    "API_KEY": RESULTS_API_KEY,
}

# How far back to look for played matches - the daily update_results.py run
# merges each day's response into the growing results archive, so this only
# needs to comfortably span the gap between runs, not the whole season.
RESULTS_WINDOW_DAYS = 21

# Search results carry only a combined "Home vs. Away | Competition" title,
# not separate team fields - and team names carry a gendered suffix to
# disambiguate from the men's team sharing the same club brand (this is a
# combined men's+women's football association site). This is the FAW's own
# site's own name-cleaning regex (found in match-hub-facetwp.js, used to
# clean names for on-page display) - reused here rather than inventing a
# different stripping rule, so names match what the FAW's own site shows.
NAME_SUFFIX_RE = re.compile(
    r"\s+(?:A|W)?FC|\s+BGC|\s+Women(?:['’]s)?|CPDM(?:\s+Y)?|CPD(?:\s+Y)?|_ Spare",
    re.IGNORECASE,
)


def _clean_team_name(name: str) -> str:
    return NAME_SUFFIX_RE.sub("", name).strip()


def _to_uk_local(epoch_ms: int) -> str:
    utc_dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    uk_dt = utc_dt.astimezone(ZoneInfo("Europe/London"))
    return uk_dt.strftime("%Y-%m-%d %H:%M")


def _parse_teams(title: str) -> tuple[str, str] | None:
    match_part = title.split(" | ", 1)[0]
    if " vs. " not in match_part:
        return None
    home, away = match_part.split(" vs. ", 1)
    return _clean_team_name(home), _clean_team_name(away)


def scrape_adran_premier() -> pd.DataFrame:
    now_ms = int(time.time() * 1000)
    params = {
        "q": "*",
        "query_by": "title",
        "filter_by": f'theme:="{THEME}" && date:>={now_ms}',
        "sort_by": "date:asc",
        "per_page": 250,
    }
    response = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return parse_adran_premier_matches(response.json())


def parse_adran_premier_matches(payload: dict) -> pd.DataFrame:
    rows = []

    for hit in payload.get("hits", []):
        doc = hit.get("document", {})
        title = doc.get("title", "")
        epoch_ms = doc.get("date")

        teams = _parse_teams(title)
        if not teams or epoch_ms is None:
            continue

        home, away = teams

        rows.append(
            {
                "competition": COMPETITION,
                "home_team": home,
                "away_team": away,
                "kickoff_uk": _to_uk_local(epoch_ms),
                "venue": "-",
                "watch_platforms": "",
                "watch_notes": "",
                "official_source": FIXTURES_PAGE_URL,
            }
        )

    return build_df(rows)


def scrape_adran_premier_results() -> pd.DataFrame:
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - RESULTS_WINDOW_DAYS * 24 * 60 * 60 * 1000
    params = {
        "q": "*",
        "query_by": "title",
        "filter_by": f'theme:="{THEME}" && date:>={window_start_ms} && date:<={now_ms}',
        "sort_by": "date:desc",
        "per_page": 250,
    }
    response = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    comet_ids = _extract_comet_ids(response.json())

    rows = []
    for comet_id in comet_ids:
        match = _fetch_match_result(comet_id)
        if match:
            rows.append(match)

    return build_results_df(rows)


def _extract_comet_ids(payload: dict) -> list[int]:
    comet_ids = []
    for hit in payload.get("hits", []):
        doc = hit.get("document", {})
        comet_id = doc.get("comet_id")
        if comet_id is not None:
            comet_ids.append(comet_id)
    return comet_ids


def _fetch_match_result(comet_id: int) -> dict | None:
    url = RESULTS_URL.format(comet_id=comet_id)
    response = requests.get(url, headers=RESULTS_HEADERS, timeout=30)
    response.raise_for_status()
    return parse_adran_premier_result(response.json())


def parse_adran_premier_result(match: dict) -> dict | None:
    if match.get("liveStatus") != "PLAYED":
        return None

    home_result = match.get("homeTeamResult", {})
    away_result = match.get("awayTeamResult", {})
    epoch_ms = match.get("dateTimeUTC")
    home_team = match.get("homeTeam", {}).get("name")
    away_team = match.get("awayTeam", {}).get("name")

    if (
        epoch_ms is None
        or not home_team
        or not away_team
        or "current" not in home_result
        or "current" not in away_result
    ):
        return None

    return {
        "competition": COMPETITION,
        "home_team": _clean_team_name(home_team),
        "away_team": _clean_team_name(away_team),
        "kickoff_uk": _to_uk_local(epoch_ms),
        "venue": match.get("facility", {}).get("name", "-"),
        "home_score": home_result["current"],
        "away_score": away_result["current"],
        "official_source": FIXTURES_PAGE_URL,
    }
