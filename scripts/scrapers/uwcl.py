from __future__ import annotations

import re
from datetime import date, datetime

from .common import build_df, fetch_lines

UWCL_URL = "https://www.live-footballontv.com/womens-champions-league-on-tv.html"
COMPETITION = "UEFA Women's Champions League"

DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\s+(\d{4})$",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
MATCH_RE = re.compile(r"^(.+?)\s+v\s+(.+?)$", re.IGNORECASE)
ROUND_RE = re.compile(r"^Women's Champions League", re.IGNORECASE)

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def parse_listing_date(line: str):
    m = DATE_RE.match(line.strip())
    if not m:
        return None
    _, day, month_name, year = m.groups()
    return date(int(year), MONTHS[month_name.title()], int(day))


def normalise_watch_line(line: str) -> str:
    # Fix the stuck-together BBC/Disney+ text seen on the page
    replacements = [
        ("BBC iPlayer Disney+", "BBC iPlayer, Disney+"),
        ("Disney+BBC Sport Website", "Disney+, BBC Sport Website"),
        ("BBC Two BBC iPlayer", "BBC Two, BBC iPlayer"),
    ]
    for old, new in replacements:
        line = line.replace(old, new)

    # collapse repeated spaces and standardise commas
    parts = [part.strip() for part in re.split(r",|\s{2,}", line) if part.strip()]
    if parts:
        return ", ".join(parts)
    return line.strip()


def scrape_uwcl():
    lines = fetch_lines(UWCL_URL)
    return parse_uwcl_lines(lines)


def parse_uwcl_lines(lines):
    rows = []

    current_date = None
    today = date.today()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        parsed_date = parse_listing_date(line)
        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        if not current_date:
            i += 1
            continue

        if TIME_RE.match(line):
            kickoff_time = line

            match_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            round_line = lines[i + 2].strip() if i + 2 < len(lines) else ""
            watch_line = lines[i + 3].strip() if i + 3 < len(lines) else ""

            match_match = MATCH_RE.match(match_line)
            if not match_match:
                i += 1
                continue

            home_team, away_team = match_match.groups()

            if current_date < today:
                i += 1
                continue

            competition_name = COMPETITION
            watch_notes = ""

            if ROUND_RE.match(round_line):
                competition_name = f"{COMPETITION} - {round_line}"

            watch_platforms = normalise_watch_line(watch_line) if watch_line else ""

            rows.append(
                {
                    "competition": competition_name,
                    "home_team": home_team.strip(),
                    "away_team": away_team.strip(),
                    "kickoff_uk": f"{current_date.isoformat()} {kickoff_time}",
                    "venue": "TBC",
                    "watch_platforms": watch_platforms,
                    "watch_notes": watch_notes,
                    "official_source": UWCL_URL,
                }
            )

            i += 4
            continue

        i += 1

    return build_df(rows)