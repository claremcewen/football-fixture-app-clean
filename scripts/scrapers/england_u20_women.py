from __future__ import annotations

import re
from datetime import date

from .common import (
    build_df,
    fetch_lines,
    parse_bst_gmt_time,
    parse_england_date,
)

U20_URL = "https://www.englandfootball.com/england/youth/Womens-U20"
COMPETITION_LABEL = "England Women U20"
WORLD_CUP_LABEL = "FIFA U20 Women's World Cup"

# Unlike the senior team's page, month headers here sometimes carry a comma
# ("August, 2026") and sometimes don't ("September 2026") - no consistent
# rule found, so the comma is just optional.
MONTH_YEAR_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|"
    r"November|December),?\s+(\d{4})$"
)
BARE_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")

# Scanning backward from a match's date line to find its competition name
# (and venue, if listed) - stop at whichever comes first: a month header,
# a completed-match's own trailing markers ("MATCH REPORT", "FT"), or the
# previous match's own bare kickoff-time line. There's no fixed number of
# lines between one match and the competition name for the next - a World
# Cup fixture has a venue line, a friendly usually doesn't.
CONTEXT_STOP_MARKERS = {"MATCH REPORT", "FT"}
MAX_CONTEXT_LOOKBACK = 4


def scrape_england_u20_women():
    lines = fetch_lines(U20_URL)
    return parse_england_u20_lines(lines)


def _collect_competition_context(lines: list[str], date_index: int) -> list[str]:
    context = []
    j = date_index - 1
    while j >= 0 and len(context) < MAX_CONTEXT_LOOKBACK:
        prev = lines[j].strip()
        if (
            not prev
            or prev in CONTEXT_STOP_MARKERS
            or MONTH_YEAR_RE.match(prev)
            or BARE_TIME_RE.match(prev)
        ):
            break
        context.append(prev)
        j -= 1
    context.reverse()
    return context


def parse_england_u20_lines(lines):
    rows = []
    current_year = None
    today = date.today()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        month_match = MONTH_YEAR_RE.match(line)
        if month_match:
            current_year = int(month_match.group(2))
            i += 1
            continue

        if current_year is None:
            i += 1
            continue

        parsed_date = parse_england_date(line, current_year)
        if (
            parsed_date
            and i + 5 < len(lines)
            and lines[i + 1].strip() == "|"
            and parse_bst_gmt_time(lines[i + 2].strip())
            and lines[i + 3].strip() == "Fixture"
        ):
            kickoff_time = parse_bst_gmt_time(lines[i + 2].strip())
            first_team = lines[i + 4].strip()
            second_team = lines[i + 5].strip()

            # Only upcoming ("Fixture") rows are captured at all - completed
            # matches are tagged "Results" instead and skipped entirely,
            # same convention as the senior team's scraper.
            if parsed_date < today:
                i += 6
                continue

            home_team, away_team = first_team, second_team
            if first_team == "England":
                home_team, away_team = "England", second_team
            elif second_team == "England":
                home_team, away_team = first_team, "England"

            context = _collect_competition_context(lines, i)
            is_world_cup = any("world cup" in c.lower() for c in context)
            competition_name = WORLD_CUP_LABEL if is_world_cup else "Friendly"
            venue = context[-1] if len(context) >= 3 else "-"

            rows.append(
                {
                    "competition": f"{COMPETITION_LABEL} - {competition_name}",
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": f"{parsed_date.isoformat()} {kickoff_time}",
                    "venue": venue,
                    "watch_platforms": "",
                    "watch_notes": "",
                    "official_source": U20_URL,
                }
            )
            i += 6
            continue

        i += 1

    return build_df(rows)
