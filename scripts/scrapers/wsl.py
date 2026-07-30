from __future__ import annotations

import re
from datetime import datetime

from .common import build_df, fetch_lines

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"

STOP_MARKERS = {
    "© 2025 Women's Super League Football Ltd. All rights reserved.",
    "Back to top",
    "Privacy Settings & Cookie Management",
}

# Per-match day header, e.g. "Fri 4 Sep" - no year, so the matchweek's own
# date-range line (parsed separately, below) supplies it.
DAY_HEADER_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3})$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
TRAILING_YEAR_RE = re.compile(r"(\d{4})\s*$")


def parse_match_day(line: str, year: int):
    m = DAY_HEADER_RE.match(line.strip())
    if not m:
        return None
    _, day, month_abbrev = m.groups()
    month_num = datetime.strptime(month_abbrev.title(), "%b").month
    return datetime(year, month_num, int(day)).date()


def extract_year(line: str) -> int | None:
    m = TRAILING_YEAR_RE.search(line.strip())
    return int(m.group(1)) if m else None


def scrape_wsl():
    lines = fetch_lines(WSL_URL)
    return parse_wsl_lines(lines)


def parse_wsl_lines(lines):
    rows = []

    current_year = datetime.today().year
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line in STOP_MARKERS:
            break

        if line.startswith("Matchweek"):
            # The following line is the matchweek's own date range (e.g.
            # "4–6 September 2026", or "Date to be confirmed" if unset) -
            # only the year matters here; per-match day headers below are
            # day/month only and rely on this for the year.
            if i + 1 < len(lines):
                year = extract_year(lines[i + 1])
                if year:
                    current_year = year
            i += 1
            continue

        # Match structure (each team's name repeats 3x - full/short/code -
        # only the full name, immediately after the day header or kickoff
        # time, is used):
        # Fri 4 Sep
        # London City Lionesses / London City / LCL
        # 19:00
        # Manchester United / Man Utd / MUN
        # CopperJax Community Stadium
        # Sky Sports              <- optional, not yet confirmed for every match
        # Tickets
        match_date = parse_match_day(line, current_year)
        if (
            match_date
            and i + 7 < len(lines)
            and TIME_RE.match(lines[i + 4].strip())
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
                    "competition": COMPETITION,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": f"{match_date.isoformat()} {time_text}",
                    "venue": venue,
                    "watch_platforms": ", ".join(watch_platforms),
                    "watch_notes": "",
                    "official_source": WSL_URL,
                }
            )

            i = j + 1
            continue

        i += 1

    return build_df(rows)
