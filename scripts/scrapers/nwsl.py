from __future__ import annotations

import re
from datetime import date

from .common import build_df, fetch_lines

NWSL_URL = "https://www.live-footballontv.com/live-womens-football-on-tv.html"
COMPETITION = "NWSL"

DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\s+(\d{4})$",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
MATCH_RE = re.compile(r"^(.+?)\s+v\s+(.+?)$", re.IGNORECASE)

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# NWSL is a single round-robin, so every fixture is at the home team's own
# ground - no need to scrape venue separately. Boston and Seattle currently
# split home games across two grounds each (World Cup stadium prep); this
# lists their primary venue, so those two may occasionally be wrong.
NWSL_TEAM_VENUES = {
    "Angel City": "BMO Stadium",
    "Bay FC": "PayPal Park",
    "Boston Legacy": "Gillette Stadium",
    "Chicago Stars": "Northwestern Medicine Field",
    "Denver Summit": "Empower Field at Mile High",
    "Gotham FC": "Sports Illustrated Stadium",
    "Houston Dash": "Shell Energy Stadium",
    "Kansas City Current": "CPKC Stadium",
    "North Carolina Courage": "First Horizon Stadium",
    "Orlando Pride": "Inter&Co Stadium",
    "Portland Thorns": "Providence Park",
    "Racing Louisville": "Lynn Family Stadium",
    "San Diego Wave": "Snapdragon Stadium",
    "Seattle Reign": "Lumen Field",
    "Utah Royals": "America First Field",
    "Washington Spirit": "Audi Field",
}


def parse_listing_date(line: str):
    m = DATE_RE.match(line.strip())
    if not m:
        return None
    _, day, month_name, year = m.groups()
    return date(int(year), MONTHS[month_name.title()], int(day))


def scrape_nwsl():
    lines = fetch_lines(NWSL_URL)
    return parse_nwsl_lines(lines)


def parse_nwsl_lines(lines):
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

        if not current_date or not TIME_RE.match(line):
            i += 1
            continue

        kickoff_time = line
        match_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        competition_tag = lines[i + 2].strip() if i + 2 < len(lines) else ""

        # collect watch platform lines until the next match/date entry
        j = i + 3
        watch_platforms = []
        while j < len(lines):
            next_line = lines[j].strip()
            if TIME_RE.match(next_line) or parse_listing_date(next_line):
                break
            if next_line:
                watch_platforms.append(next_line)
            j += 1

        match_match = MATCH_RE.match(match_line)
        if (
            match_match
            and competition_tag == COMPETITION
            and current_date >= today
        ):
            home_team, away_team = match_match.groups()
            home_team = home_team.strip()
            rows.append(
                {
                    "competition": COMPETITION,
                    "home_team": home_team,
                    "away_team": away_team.strip(),
                    "kickoff_uk": f"{current_date.isoformat()} {kickoff_time}",
                    "venue": NWSL_TEAM_VENUES.get(home_team, "-"),
                    "watch_platforms": ", ".join(watch_platforms),
                    "watch_notes": "",
                    "official_source": NWSL_URL,
                }
            )

        i = j
        continue

    return build_df(rows)
