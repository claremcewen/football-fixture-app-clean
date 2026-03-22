
from __future__ import annotations

import re
from datetime import date
import pandas as pd

from .common import (
    ENGLAND_TIME_RE,
    build_df,
    fetch_lines,
    parse_england_date,
    parse_bst_gmt_time,
)

ENGLAND_URL = "https://www.englandfootball.com/england/womens-senior-team/fixtures-results"
COMPETITION_LABEL = "England Women"
MONTH_YEAR_RE = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$")


def scrape_england_women() -> "pd.DataFrame":


    lines = fetch_lines(ENGLAND_URL)
    rows = []

    current_year = None
    current_month_label = None
    today = date.today()

    i = 0
    while i < len(lines):
        line = lines[i]

        month_match = MONTH_YEAR_RE.match(line)
        if month_match:
            current_month_label, year_text = month_match.groups()
            current_year = int(year_text)
            i += 1
            continue

        if current_year is None:
            i += 1
            continue

        parsed_date = parse_england_date(line, current_year)
        if parsed_date:
            status = lines[i + 1] if i + 1 < len(lines) else ""
            if status != "Fixture":
                i += 1
                continue

            first_team = lines[i + 2] if i + 2 < len(lines) else ""
            second_team = lines[i + 3] if i + 3 < len(lines) else ""
            venue = lines[i + 4] if i + 4 < len(lines) else "TBC"
            time_or_tbc = lines[i + 5] if i + 5 < len(lines) else "TBC"

            # Skip past fixtures/results older than today
            if parsed_date < today:
                i += 1
                continue

            home_team = first_team
            away_team = second_team
            if first_team == "England":
                home_team = "England"
                away_team = second_team
            elif second_team == "England":
                home_team = first_team
                away_team = "England"

            kickoff_time = parse_bst_gmt_time(time_or_tbc)
            if kickoff_time:
                kickoff_uk = f"{parsed_date.isoformat()} {kickoff_time}"
                watch_notes = ""
            else:
                kickoff_uk = f"{parsed_date.isoformat()} 12:00"
                watch_notes = "Kick-off time to be confirmed"

            competition_name = lines[i - 2] if i - 2 >= 0 else COMPETITION_LABEL
            if MONTH_YEAR_RE.match(competition_name or ""):
                competition_name = COMPETITION_LABEL

            rows.append(
                {
                    "competition": f"{COMPETITION_LABEL} - {competition_name}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": kickoff_uk,
                    "venue": venue,
                    "watch_platforms": "",
                    "watch_notes": watch_notes,
                    "official_source": ENGLAND_URL,
                }
            )
            i += 6
            continue

        i += 1

    return build_df(rows)
