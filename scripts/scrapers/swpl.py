from __future__ import annotations

import json

import pandas as pd
import requests

from .common import build_df

API_URL = "https://swpl.uk/wp-json/swpl/v2/match-list"
FIXTURES_PAGE_URL = "https://swpl.uk/match-centre/swpl/"
COMPETITION = "SWPL 1"

# The site's own "match centre" widget calls this API client-side (found via
# the theme's JS bundle) - not a published/documented API, so it could
# change without warning, but it's a clean structured JSON response with no
# scraping fragility, same trade-off as FAWNL's api.wnl.thefa.com.
API_KEY = "AUueZwwJ2EM9o2Zj9c574PmtkndRwhA4S9b9MsWofxcn2knbYK8L4ps92Y3PGJZD"
TOURNAMENT_CALENDAR_ID = "a55oqz5coo9mgb1u6lv9lgb9w"  # 2026/27 season
COMPETITION_ID = "cydr5rltozch9qnzjurt1r7d9"  # SWPL 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WomensFootballWatchGuide/1.0)",
    "x-api-key": API_KEY,
}


def scrape_swpl() -> pd.DataFrame:
    params = {"tmcl": TOURNAMENT_CALENDAR_ID, "comp": COMPETITION_ID, "type": "fixture"}
    response = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return parse_swpl_matches(response.json())


def parse_swpl_matches(payload: dict) -> pd.DataFrame:
    rows = []

    for row in payload.get("data", []):
        match_info = json.loads(row["data"])["matchInfo"]
        contestants = match_info.get("contestant", [])

        home = next((c for c in contestants if c.get("position") == "home"), None)
        away = next((c for c in contestants if c.get("position") == "away"), None)

        match_date = match_info.get("localDate")
        match_time = match_info.get("localTime")

        if not (home and away and match_date and match_time):
            continue

        venue = match_info.get("venue", {}).get("shortName", "-")

        rows.append(
            {
                "competition": COMPETITION,
                "home_team": home["name"],
                "away_team": away["name"],
                # localTime includes seconds ("14:00:00") - trimmed to HH:MM
                # to match this project's kickoff_uk convention.
                "kickoff_uk": f"{match_date} {match_time[:5]}",
                "venue": venue,
                "watch_platforms": "",
                "watch_notes": "",
                "official_source": FIXTURES_PAGE_URL,
            }
        )

    return build_df(rows)
