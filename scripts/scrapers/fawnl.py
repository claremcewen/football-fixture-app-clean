from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from .common import build_df

API_URL = "https://api.wnl.thefa.com/matches"
TENANT_ID = "wnl"
FIXTURES_PAGE_URL = "https://wnl.thefa.com/fixtures"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WomensFootballWatchGuide/1.0)",
    "X-TENANT-ID": TENANT_ID,
}

# The FA's own site groups these under one "FA Women's National League" brand,
# but tier 3 (national) and tier 4 (regional) are genuinely different
# competitions - each division gets its own competition_group downstream via
# registry.py, keyed off these exact names as returned by the API. The Cup
# is cross-divisional (open to tier 3 and 4 clubs alike), so it isn't tied
# to one tier the way the six league divisions are.
DIVISION_COMPETITION_IDS = {
    "Northern Premier Division": "6a1fd7394a65cd341c5db8f1",
    "Southern Premier Division": "6a1fd7694a65cd341c5db8f2",
    "Division 1 North": "6a1fd78a4a65cd341c5db8f3",
    "Division 1 Midlands": "6a1fd7a94a65cd341c5db8f4",
    "Division 1 South East": "6a1fd7c94a65cd341c5db8f5",
    "Division 1 South West": "6a1fd7e94a65cd341c5db8f6",
}
CUP_COMPETITION_IDS = {
    "The FA Women's National League Cup": "6a573005020f1fa3730a344b",
}
ALL_COMPETITION_IDS = {**DIVISION_COMPETITION_IDS, **CUP_COMPETITION_IDS}

# Home ground per club, kept in a CSV (not hardcoded here) so it's easy to
# maintain without touching code - two columns, "team,venue". The FA's own
# system has this field empty for every fixture (checked all 72 league
# clubs), so unlike NWSL there's no venue data to derive at all. These are
# semi-professional/amateur sides, many sharing a name with an unrelated
# men's club playing at a completely different (and much smaller) ground,
# so guessing from general knowledge would often be wrong - fill this file
# in as grounds are confirmed. Unmapped/blank teams fall back to "-".
VENUES_FILE = Path(__file__).resolve().parents[2] / "data" / "fawnl_venues.csv"

# How far ahead to request fixtures for - comfortably covers a full season
# (mid-August through early May) regardless of which day this runs.
FIXTURE_WINDOW_DAYS = 300


def load_venue_lookup() -> dict[str, str]:
    if not VENUES_FILE.exists():
        return {}

    venues_df = pd.read_csv(VENUES_FILE)
    venues_df["venue"] = venues_df["venue"].fillna("").astype(str).str.strip()
    return {
        row["team"]: row["venue"]
        for _, row in venues_df.iterrows()
        if row["venue"]
    }


def scrape_fawnl() -> pd.DataFrame:
    today = date.today()
    params = {
        "limit": 1000,
        "period": "Custom",
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=FIXTURE_WINDOW_DAYS)).isoformat(),
        "sort": "asc",
        "status": "fixture",
        "competition": ",".join(ALL_COMPETITION_IDS.values()),
    }
    response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return parse_fawnl_matches(response.json())


def parse_fawnl_matches(data: dict) -> pd.DataFrame:
    venue_lookup = load_venue_lookup()
    rows = []

    for match in data.get("items", []):
        home_team = match["homeTeam"]["fullName"]
        away_team = match["awayTeam"]["fullName"]
        competition_name = match["competition"]["name"]
        match_date = match.get("date")
        match_time = match.get("time")

        if not match_date or not match_time:
            continue

        rows.append(
            {
                "competition": competition_name,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff_uk": f"{match_date} {match_time}",
                "venue": venue_lookup.get(home_team, "-"),
                "watch_platforms": "",
                "watch_notes": "",
                "official_source": FIXTURES_PAGE_URL,
            }
        )

    return build_df(rows)
