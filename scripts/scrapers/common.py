
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WomensFootballWatchGuide/1.0)"
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

DAY_HEADER_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Za-z]+) (\d{1,2}), (\d{4})$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s?[AP]M$", re.I)
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


def month_number(name: str) -> int:
    return MONTH_NAME_TO_NUMBER[name]


def parse_day_header(line: str):
    m = DAY_HEADER_RE.match(line)
    if not m:
        return None
    _, month_name, day, year = m.groups()
    return datetime(int(year), month_number(month_name), int(day)).date()


def parse_us_time(time_text: str) -> str:
    return datetime.strptime(time_text.upper().replace(" ", ""), "%I:%M%p").strftime("%H:%M")


def to_uk_iso(date_obj, time_text: str) -> str:
    return f"{date_obj.isoformat()} {parse_us_time(time_text)}"


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


# wslfootball.com has been observed flipping between two completely
# different page templates for the same fixtures (twice within a week) -
# scrapers for that site try both parsers below on the same fetched lines
# and use whichever one actually finds matches, rather than assuming
# either template is stable.

WSL_STOP_MARKERS = {
    "© 2025 Women's Super League Football Ltd. All rights reserved.",
    "Back to top",
    "Privacy Settings & Cookie Management",
}

WSL_SHORT_DAY_HEADER_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3})$")
WSL_TIME_24H_RE = re.compile(r"^\d{1,2}:\d{2}$")
WSL_TRAILING_YEAR_RE = re.compile(r"(\d{4})\s*$")

# Optional filler line in the legacy template, between the away team's code
# and "Tickets" - present for some matches, absent for others.
WSL_FILLER_LINES = {"Stay nearby", "Stay Nearby"}


def _parse_wsl_short_day(line: str, year: int):
    m = WSL_SHORT_DAY_HEADER_RE.match(line.strip())
    if not m:
        return None
    _, day, month_abbrev = m.groups()
    month_num = datetime.strptime(month_abbrev.title(), "%b").month
    return datetime(year, month_num, int(day)).date()


def parse_wslfootball_new_format(lines: list[str], competition: str, source_url: str) -> pd.DataFrame:
    """The redesigned wslfootball.com template: 24-hour times, each team's
    name repeated 3x (full/short/code), and short per-match date headers
    (e.g. "Fri 4 Sep") with the year only on the enclosing "Matchweek N"
    block's own date-range line."""
    rows = []
    current_year = datetime.today().year
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line in WSL_STOP_MARKERS:
            break

        if line.startswith("Matchweek"):
            if i + 1 < len(lines):
                m = WSL_TRAILING_YEAR_RE.search(lines[i + 1].strip())
                if m:
                    current_year = int(m.group(1))
            i += 1
            continue

        match_date = _parse_wsl_short_day(line, current_year)
        if (
            match_date
            and i + 7 < len(lines)
            and WSL_TIME_24H_RE.match(lines[i + 4].strip())
        ):
            home_team = lines[i + 1].strip()
            time_text = lines[i + 4].strip()
            away_team = lines[i + 5].strip()

            j = i + 8
            gap_lines = []
            while j < len(lines) and lines[j].strip() != "Tickets":
                gap_lines.append(lines[j].strip())
                j += 1
                if len(gap_lines) > 5:
                    break

            venue = gap_lines[0] if gap_lines else "-"
            watch_platforms = gap_lines[1:]

            rows.append(
                {
                    "competition": competition,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": f"{match_date.isoformat()} {time_text}",
                    "venue": venue,
                    "watch_platforms": ", ".join(watch_platforms),
                    "watch_notes": "",
                    "official_source": source_url,
                }
            )

            i = j + 1
            continue

        i += 1

    return build_df(rows)


def parse_wslfootball_legacy_format(lines: list[str], competition: str, source_url: str) -> pd.DataFrame:
    """wslfootball.com's older template: comma-dated day headers, a
    "sport-match-details-for"/"VS" marker pair, and 12-hour AM/PM times."""
    rows = []
    current_date = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line in WSL_STOP_MARKERS:
            break

        parsed_date = parse_day_header(line)
        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        if (
            current_date
            and line == "sport-match-details-for"
            and i + 9 < len(lines)
            and lines[i + 2].strip() == "VS"
            and TIME_RE.match(lines[i + 4].strip())
        ):
            home_team = lines[i + 1].strip()
            away_team = lines[i + 3].strip()
            time_text = lines[i + 4].strip()
            venue = lines[i + 5].strip()

            j = i + 10
            watch_platforms = []
            while j < len(lines) and lines[j].strip() in WSL_FILLER_LINES:
                j += 1

            if j < len(lines) and lines[j].strip() == "Tickets":
                j += 1
                # The broadcaster, if confirmed, is a single line right
                # after "Tickets" - anything else there (next match's date
                # header, or the page footer nav once this is the last
                # match on the page) is NOT part of this match, so only
                # ever look at this one line, never loop further.
                if (
                    j < len(lines)
                    and lines[j].strip()
                    and not parse_day_header(lines[j].strip())
                    and lines[j].strip() not in WSL_STOP_MARKERS
                    and lines[j].strip() != "sport-match-details-for"
                ):
                    watch_platforms.append(lines[j].strip())
                    j += 1

            rows.append(
                {
                    "competition": competition,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": to_uk_iso(current_date, time_text),
                    "venue": venue,
                    "watch_platforms": ", ".join(watch_platforms),
                    "watch_notes": "",
                    "official_source": source_url,
                }
            )

            i = j
            continue

        i += 1

    return build_df(rows)


def parse_wslfootball(lines: list[str], competition: str, source_url: str) -> pd.DataFrame:
    """Try both known wslfootball.com templates and return whichever finds
    matches - the site has flipped between them without warning before."""
    df = parse_wslfootball_new_format(lines, competition, source_url)
    if not df.empty:
        return df
    return parse_wslfootball_legacy_format(lines, competition, source_url)


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
