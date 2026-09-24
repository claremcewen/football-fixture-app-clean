
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Wikipedia's bot policy rejects generic/contactless User-Agents outright
# (a bare "compatible; ..." string 403s every request, discovered while
# wiring up a Wikipedia-sourced scraper) - this one identifies the project
# and gives a real contact, satisfying that policy, and every other source
# here has been fine with a descriptive UA too.
HEADERS = {
    "User-Agent": (
        "WomensFootballWatchGuide/1.0 "
        "(https://she-can-kick-it-fixtures.streamlit.app; contact: claremcewen@gmail.com)"
    )
}

MONTH_NAME_TO_NUMBER = {
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

ENGLAND_DATE_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})(?:ST|ND|RD|TH)\s+([A-Za-z]{3})$", re.I)
ENGLAND_TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s+(BST|GMT)$", re.I)
LINK_REF_RE = re.compile(r"^https?://", re.I)


def fetch_lines(url: str) -> list[str]:
    last_error = None

    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text("\n")
            lines = [clean_line(line) for line in text.splitlines()]
            return [line for line in lines if line]
        except requests.RequestException as exc:
            last_error = exc
            print(f"Attempt {attempt + 1} failed for {url}: {exc}")

    raise last_error

def fetch_html(url: str) -> str:
    last_error = None

    for attempt in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
            print(f"Attempt {attempt + 1} failed for {url}: {exc}")

    raise last_error


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def to_uk_iso_from_tz(date_obj, time_text: str, source_tz: str) -> str:
    """Combine a date + 24h time in the given source timezone and return the
    equivalent UK local time as a 'YYYY-MM-DD HH:MM' string. Needed for
    sources (e.g. WAFCON's Wikipedia page) that publish kickoff times in the
    host country's own local time rather than already-converted UK time."""
    hour, minute = (int(part) for part in time_text.split(":"))
    local_dt = datetime(
        date_obj.year, date_obj.month, date_obj.day, hour, minute,
        tzinfo=ZoneInfo(source_tz),
    )
    uk_dt = local_dt.astimezone(ZoneInfo("Europe/London"))
    return uk_dt.strftime("%Y-%m-%d %H:%M")


LIVE_FOOTBALL_ON_TV_DATE_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]+)\s+(\d{4})$",
    re.IGNORECASE,
)

# Footer/nav content immediately follows the last fixture in the list, with
# no time/date line of its own to signal "stop collecting broadcaster
# lines" - same problem NWSL's own scraper guards against.
LIVE_FOOTBALL_ON_TV_STOP_MARKERS = {
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


def _parse_live_football_on_tv_date(line: str):
    m = LIVE_FOOTBALL_ON_TV_DATE_RE.match(line.strip())
    if not m:
        return None
    day, month_name, year = m.groups()
    return datetime(int(year), MONTH_NAME_TO_NUMBER[month_name.title()], int(day)).date()


def build_watch_platform_lookup(url: str, team_name: str) -> dict:
    """Scan a live-footballontv.com-style listing page for every match
    involving team_name (matched exactly against one side of a "Home v
    Away" line) and return a {date: watch_platforms string} lookup.

    Built for sources (e.g. englandfootball.com) that don't publish
    broadcaster info themselves - matched by date alone rather than by
    team name text, since England only plays one match a day and team
    names are formatted differently between sites ("England" vs "England
    Women" vs "England Women U20"). A kickoff time of "TBC" is treated the
    same as a real HH:MM time for the purpose of finding where one match's
    entry ends and the next begins - international broadcaster
    announcements often land before the kickoff time itself is confirmed.
    """
    lines = fetch_lines(url)
    return parse_watch_platform_lookup_lines(lines, team_name)


def parse_watch_platform_lookup_lines(lines, team_name: str) -> dict:
    lookup: dict = {}

    current_date = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        parsed_date = _parse_live_football_on_tv_date(line)
        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        if " v " in line and current_date:
            home, _, away = line.partition(" v ")
            if home.strip() == team_name or away.strip() == team_name:
                # Skip the competition-tag line right after the match line,
                # then collect broadcaster lines until the next time/TBC/
                # date/stop-marker entry.
                j = i + 2
                platforms = []
                while j < len(lines):
                    next_line = lines[j].strip()
                    if (
                        re.match(r"^\d{1,2}:\d{2}$", next_line)
                        or next_line == "TBC"
                        or _parse_live_football_on_tv_date(next_line)
                        or next_line in LIVE_FOOTBALL_ON_TV_STOP_MARKERS
                    ):
                        break
                    if next_line:
                        platforms.append(next_line)
                    j += 1
                if platforms:
                    lookup[current_date] = ", ".join(platforms)
                i = j
                continue

        i += 1

    return lookup


# wslfootball.com's visible fixture/results text is client-rendered and has
# flipped between incompatible templates before (a real, previously-hit
# reliability problem) - but the *full* match data for the whole season
# (every round, fixtures and finished results together, with score,
# broadcaster and venue) ships as plain JSON in the page's initial server
# response, embedded inside Next.js's streaming payload
# (`self.__next_f.push(...)` script calls). A naive text-scrape of the
# rendered page never saw this - it's not in the visible text, just script
# content - but it's genuinely more complete and reliable once extracted,
# and immune to the site's visible-template flips since it never depended
# on that layout at all.
WSLFOOTBALL_CHUNK_RE = re.compile(r"self\.__next_f\.push\(\[1,(\".*?\")\]\)", re.DOTALL)
WSLFOOTBALL_MATCH_ID_RE = re.compile(r'"matchId":"wpll::Football_Match::([a-f0-9]+)"')


def _extract_json_object(text: str, start_idx: int) -> str | None:
    """Given the index of a JSON object's opening '{', returns the full
    balanced object as a string - a plain non-greedy regex can't do this
    correctly since nested objects (team info, editorial data) have their
    own braces; this tracks string state so quoted braces don't throw off
    the depth count."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start_idx : i + 1]
    return None


def fetch_wslfootball_matches(url: str) -> list[dict]:
    """Fetches a wslfootball.com fixtures page and returns every match
    object embedded in it (the whole season, fixtures and results both) as
    raw dicts - see the module comment above for why this beats scraping
    the rendered page's visible text."""
    html = fetch_html(url)

    chunks = WSLFOOTBALL_CHUNK_RE.findall(html)
    full_text = "".join(json.loads(chunk) for chunk in chunks)

    matches = []
    seen_ids = set()
    for match in WSLFOOTBALL_MATCH_ID_RE.finditer(full_text):
        match_id = match.group(1)
        if match_id in seen_ids:
            continue

        # Walk backward from the matchId key to the '{' that opens its
        # enclosing match object, tracking brace depth so an earlier nested
        # object (e.g. from the previous match) isn't mistaken for the start.
        depth = 0
        start = match.start()
        while start > 0:
            if full_text[start] == "}":
                depth += 1
            elif full_text[start] == "{":
                if depth == 0:
                    break
                depth -= 1
            start -= 1

        obj_text = _extract_json_object(full_text, start)
        if not obj_text:
            continue
        try:
            obj = json.loads(obj_text)
        except json.JSONDecodeError:
            continue
        if "home" in obj and "away" in obj:
            matches.append(obj)
            seen_ids.add(match_id)

    return matches


def _wslfootball_broadcaster(match: dict) -> str:
    broadcasters = match.get("editorial", {}).get("broadcasters", {}) or {}
    # "Name|https://url" - only the name is ever shown elsewhere in this app.
    return broadcasters.get("broadcasterNational1", "").split("|", 1)[0].strip()


def _wslfootball_kickoff_uk(match: dict) -> str | None:
    # matchDateLocal is already UK local time (localTimeUtcOffset confirms
    # it), unlike matchDateUtc - no separate timezone conversion needed.
    local = match.get("matchDateLocal")
    return local[:16].replace("T", " ") if local else None


def wslfootball_fixtures_df(matches: list[dict], competition: str, source_url: str) -> pd.DataFrame:
    rows = []
    for m in matches:
        if m.get("status") == "FINISHED":
            continue
        kickoff_uk = _wslfootball_kickoff_uk(m)
        if not kickoff_uk:
            continue
        rows.append(
            {
                "competition": competition,
                "home_team": m["home"]["officialName"],
                "away_team": m["away"]["officialName"],
                "kickoff_uk": kickoff_uk,
                "venue": m.get("stadiumName") or "-",
                "watch_platforms": _wslfootball_broadcaster(m),
                "watch_notes": "",
                "official_source": source_url,
            }
        )
    return build_df(rows)


def wslfootball_results_df(matches: list[dict], competition: str, source_url: str) -> pd.DataFrame:
    rows = []
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        home_score = m.get("homeScorePush")
        away_score = m.get("awayScorePush")
        kickoff_uk = _wslfootball_kickoff_uk(m)
        if home_score is None or away_score is None or not kickoff_uk:
            continue
        rows.append(
            {
                "competition": competition,
                "home_team": m["home"]["officialName"],
                "away_team": m["away"]["officialName"],
                "kickoff_uk": kickoff_uk,
                "venue": m.get("stadiumName") or "-",
                "home_score": home_score,
                "away_score": away_score,
                "official_source": source_url,
            }
        )
    return build_results_df(rows)


def build_df(rows: Iterable[dict]) -> pd.DataFrame:
    columns = [
        "competition",
        "sport",
        "competition_group",
        "region",
        "tier",
        "home_team",
        "away_team",
        "kickoff_uk",
        "venue",
        "watch_platforms",
        "watch_notes",
        "official_source",
    ]
    df = pd.DataFrame(list(rows), columns=columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df


# Same shape as build_df's fixture rows, but for played matches: swaps the
# broadcast-related columns (watch_platforms/watch_notes) for a final score,
# since neither applies once a match is over.
RESULTS_COLUMNS = [
    "competition",
    "sport",
    "competition_group",
    "region",
    "tier",
    "home_team",
    "away_team",
    "kickoff_uk",
    "venue",
    "home_score",
    "away_score",
    "official_source",
]


def build_results_df(rows: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(list(rows), columns=RESULTS_COLUMNS)
    if df.empty:
        return pd.DataFrame(columns=RESULTS_COLUMNS)
    return df


GRID_SCORE_RE = re.compile(r"^(\d+)\s*[–-]\s*(\d+)")


def parse_wikipedia_results_grid(html: str) -> list[dict]:
    """Parses a Wikipedia football season article's "Home \\ Away" results
    grid (a square matrix, one row and one matching column per team) into
    score-only rows: {home_team, away_team, home_score, away_score}.

    Deliberately doesn't return a kickoff date - once a match is played,
    the grid's cell holds its score instead of its originally-scheduled
    date (which the cell shows for not-yet-played fixtures), so there's no
    date left to read on this page at all for a played match. Pair this
    with a source that already knows the date - this project's own daily
    fixture scrape, captured into a persistent archive before it ages out
    of the forward-only fixtures file - to recover it.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows_out: list[dict] = []

    for table in soup.find_all("table", class_="wikitable"):
        trs = table.find_all("tr")
        if not trs:
            continue

        header_cells = trs[0].find_all(["th", "td"])
        if not header_cells or "\\" not in header_cells[0].get_text():
            continue  # not the results grid - some other table on the page

        team_names = [tr.find(["th", "td"]).get_text(strip=True) for tr in trs[1:] if tr.find(["th", "td"])]

        for row_idx, tr in enumerate(trs[1:]):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            home_team = cells[0].get_text(strip=True)

            for col_idx, cell in enumerate(cells[1:]):
                if col_idx >= len(team_names):
                    continue
                score_match = GRID_SCORE_RE.match(cell.get_text(" ", strip=True))
                if not score_match:
                    continue  # blank (self), or still just a future date

                rows_out.append(
                    {
                        "home_team": home_team,
                        "away_team": team_names[col_idx],
                        "home_score": int(score_match.group(1)),
                        "away_score": int(score_match.group(2)),
                    }
                )

        break  # only one results grid per page

    return rows_out


def parse_england_date(date_text: str, current_year: int):
    m = ENGLAND_DATE_RE.match(date_text)
    if not m:
        return None
    _, day, month_abbrev = m.groups()
    month_num = datetime.strptime(month_abbrev.title(), "%b").month
    return datetime(current_year, month_num, int(day)).date()


def parse_bst_gmt_time(time_text: str) -> str | None:
    m = ENGLAND_TIME_RE.match(time_text)
    if not m:
        return None
    return datetime.strptime(time_text[:5], "%H:%M").strftime("%H:%M")
