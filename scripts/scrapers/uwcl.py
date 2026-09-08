from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup

from .common import build_df, build_results_df, fetch_html, fetch_lines, to_uk_iso_from_tz

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
                    "venue": "-",
                    "watch_platforms": watch_platforms,
                    "watch_notes": watch_notes,
                    "official_source": UWCL_URL,
                }
            )

            i += 4
            continue

        i += 1

    return build_df(rows)


# uefa.com itself (the obvious source for results) is unreachable from this
# project's environments - every fetch attempt just times out, no HTTP
# response at all, not even an error page. Wikipedia's season articles use a
# standard "footballbox" template (the same one wafcon.py already parses)
# with a clean score field per match, so results come from there instead.
# Bumped once a year to that season's article titles - the qualifying
# rounds happen first (July/Aug), then the league phase (Sept-Dec); the
# knockout stage gets its own article too, added here once it exists.
RESULTS_SOURCE_URLS = [
    "https://en.wikipedia.org/wiki/2026-27_UEFA_Women%27s_Champions_League_qualifying_rounds",
    "https://en.wikipedia.org/wiki/2026-27_UEFA_Women%27s_Champions_League_league_phase",
]
RESULTS_COMPETITION = "UEFA Women's Champions League"

# Wikipedia explicitly documents that unparenthesised kickoff times on these
# pages are "as listed by UEFA" - UEFA's own broadcast convention, which is
# Central European (Summer) Time, not each match's own host-country local
# time (that's what the parenthetical, when present, is for - not needed
# here since the CET/CEST value converts to UK time correctly on its own).
UEFA_LISTED_TZ = "Europe/Paris"

# How far back to look for played matches - the daily update_results.py run
# merges each day's response into the growing results archive, so this only
# needs to comfortably span the gap between runs, not the whole season.
RESULTS_WINDOW_DAYS = 21

SCORE_RE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
RESULT_TIME_RE = re.compile(r"^(\d{1,2}:\d{2})")


def scrape_uwcl_results():
    rows = []
    for url in RESULTS_SOURCE_URLS:
        html = fetch_html(url)
        rows.extend(_parse_uwcl_results_html(html, url))
    return build_results_df(rows)


def _parse_uwcl_results_html(html: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cutoff = date.today() - timedelta(days=RESULTS_WINDOW_DAYS)
    rows = []

    for box in soup.find_all("div", class_="footballbox"):
        home = box.select_one("th.fhome span[itemprop=name]")
        away = box.select_one("th.faway span[itemprop=name]")
        score_el = box.select_one("th.fscore")
        date_el = box.select_one(".fdate .bday")
        time_el = box.select_one(".ftime")

        if not (home and away and score_el and date_el and time_el):
            continue

        score_match = SCORE_RE.search(score_el.get_text(" ", strip=True))
        if not score_match:
            continue  # not yet played ("v"), or a walkover/no-score entry

        try:
            match_date = datetime.strptime(date_el.get_text(strip=True), "%Y-%m-%d").date()
        except ValueError:
            continue
        if match_date < cutoff or match_date > date.today():
            continue

        time_match = RESULT_TIME_RE.match(time_el.get_text(strip=True))
        if not time_match:
            continue

        venue_el = box.select_one(".fright [itemprop=location] [itemprop=name]")

        rows.append(
            {
                "competition": RESULTS_COMPETITION,
                "home_team": home.get_text(" ", strip=True),
                "away_team": away.get_text(" ", strip=True),
                "kickoff_uk": to_uk_iso_from_tz(match_date, time_match.group(1), UEFA_LISTED_TZ),
                "venue": venue_el.get_text(" ", strip=True) if venue_el else "-",
                "home_score": int(score_match.group(1)),
                "away_score": int(score_match.group(2)),
                "official_source": source_url,
            }
        )

    return rows