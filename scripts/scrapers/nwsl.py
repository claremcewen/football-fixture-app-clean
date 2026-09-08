from __future__ import annotations

import re
from datetime import date

from .common import build_df, fetch_html, fetch_lines, parse_wikipedia_results_grid

NWSL_URL = "https://www.live-footballontv.com/live-womens-football-on-tv.html"
COMPETITION = "NWSL"

# live-footballontv.com (used for fixtures above) is a broadcast listing,
# never scores. See wsl.py's WSL_RESULTS_URL comment for the general
# approach - same Wikipedia-grid-plus-our-own-fixture-dates fix here.
NWSL_RESULTS_URL = "https://en.wikipedia.org/wiki/2026_NWSL_season"

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

# The last match in the scraped list is followed immediately by page
# footer/nav content, not another time/date line - without a stop marker,
# that whole footer gets slurped into the last match's watch_platforms.
STOP_MARKERS = {
    "View Our Women's Football TV Schedule by Team",
    "Back to Top",
    "Live Football On TV",
    "View All Matches",
    "View by Competition",
    "View by Team",
    "View by Channel",
    "About",
    "About Us",
    "My Guide",
    "Privacy Policy",
    "Privacy Options",
    "Contact Us",
    "Twitter",
    "Site Map",
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
            if (
                TIME_RE.match(next_line)
                or parse_listing_date(next_line)
                or next_line in STOP_MARKERS
            ):
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


# Wikipedia's grid uses each club's full "... FC" name; live-footballontv.com
# (and this file's own NWSL_TEAM_VENUES above) drops "FC" for every club
# except the two where it's the only thing distinguishing the name from a
# bare place name ("Bay", "Gotham") - checked all 16 directly against
# NWSL_TEAM_VENUES's keys rather than guessing a general stripping rule.
NWSL_WIKIPEDIA_NAME_MAP = {
    "Boston Legacy FC": "Boston Legacy",
    "Chicago Stars FC": "Chicago Stars",
    "Denver Summit FC": "Denver Summit",
    "Angel City FC": "Angel City",
    "Racing Louisville FC": "Racing Louisville",
    "Portland Thorns FC": "Portland Thorns",
    "San Diego Wave FC": "San Diego Wave",
    "Seattle Reign FC": "Seattle Reign",
}


def scrape_nwsl_grid_scores() -> list[dict]:
    html = fetch_html(NWSL_RESULTS_URL)
    rows = parse_wikipedia_results_grid(html)
    for row in rows:
        row["home_team"] = NWSL_WIKIPEDIA_NAME_MAP.get(row["home_team"], row["home_team"])
        row["away_team"] = NWSL_WIKIPEDIA_NAME_MAP.get(row["away_team"], row["away_team"])
    return rows
