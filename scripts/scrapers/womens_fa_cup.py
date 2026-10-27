from __future__ import annotations

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .common import HEADERS, build_df, build_results_df, fetch_lines

# The FA's own Women's FA Cup pages (the Adobe Women's FA Cup). Fixtures are
# plain server-rendered text; results sit behind per-round accordions that
# load via a POST (the round ids are on the results page itself and change
# every season, so they're read from it rather than hardcoded).
FIXTURES_URL = "https://www.thefa.com/competitions/the-womens-fa-cup/fixtures"
RESULTS_URL = "https://www.thefa.com/competitions/the-womens-fa-cup/results"
ROUND_RESULTS_URL = "https://www.thefa.com/Competitions/Results/FulltimeRoundMatches"
COMPETITION = "Adobe Women's FA Cup"

# Only the proper rounds - the preliminary/qualifying rounds are hundreds of
# grassroots ties nobody here is following.
PROPER_ROUND_RE = re.compile(r"(Round Proper|Quarter|Semi|^Final$)", re.IGNORECASE)

DATE_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$"
)
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
SCORE_RE = re.compile(r"^(\d+) - (\d+)$")
LIVE_ON_RE = re.compile(r"^Live on (.+)$", re.IGNORECASE)

# The FA writes clubs out in full ("Hashtag United FC Women", "Chester-Le-
# Street Town LFC") - stripped back to the short names the rest of this app
# uses for the same clubs (e.g. from the FAWNL feed).
NAME_SUFFIX_RE = re.compile(
    r"\s+(?:Women(?:'s)?(?:\s+FC)?|Ladies(?:\s+FC)?|LFC|WFC|AFC|FC)$", re.IGNORECASE
)


def _clean_team(name: str) -> str:
    name = name.strip()
    while True:
        cleaned = NAME_SUFFIX_RE.sub("", name).strip()
        if cleaned == name or not cleaned:
            return name
        name = cleaned


def _parse_date(line: str):
    m = DATE_RE.match(line)
    if not m:
        return None
    day, month_name, year = m.groups()
    try:
        return datetime.strptime(f"{day} {month_name} {year}", "%d %B %Y").date()
    except ValueError:
        return None


def parse_fixture_lines(lines: list[str]):
    rows = []
    current_date = None
    current_round = None
    i = 0
    while i < len(lines):
        line = lines[i]

        parsed_date = _parse_date(line)
        if parsed_date:
            current_date = parsed_date
            current_round = None
            i += 1
            continue

        if current_date and current_round is None and PROPER_ROUND_RE.search(line) and "Qualifying" not in line:
            current_round = line
            i += 1
            continue

        # [time, number, home, "VS", away]
        if (
            current_round
            and TIME_RE.match(line)
            and i + 4 < len(lines)
            and lines[i + 1].isdigit()
            and lines[i + 3] == "VS"
        ):
            home, away = lines[i + 2], lines[i + 4]

            watch = ""
            j = i + 5
            while j < len(lines) and not TIME_RE.match(lines[j]) and not _parse_date(lines[j]):
                live = LIVE_ON_RE.match(lines[j])
                if live:
                    watch = live.group(1).strip()
                if "Back To Top" in lines[j] or PROPER_ROUND_RE.search(lines[j]):
                    break
                j += 1

            # Later-round ties still waiting on an earlier result read
            # "Team A / Team B" - skipped until they resolve to a real club.
            if "/" not in home and "/" not in away:
                rows.append(
                    {
                        "competition": f"{COMPETITION} - {current_round}",
                        "home_team": _clean_team(home),
                        "away_team": _clean_team(away),
                        "kickoff_uk": f"{current_date.isoformat()} {lines[i]}",
                        "venue": "-",
                        "watch_platforms": watch,
                        "watch_notes": "",
                        "official_source": FIXTURES_URL,
                    }
                )
            i = j
            continue

        i += 1

    return build_df(rows)


def parse_round_results(lines: list[str], round_name: str):
    rows = []
    current_date = None
    i = 0
    while i < len(lines):
        line = lines[i]

        parsed_date = _parse_date(line)
        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        # [time, number, home, score, away]  (a postponed tie reads "P - P")
        if (
            current_date
            and TIME_RE.match(line)
            and i + 4 < len(lines)
            and lines[i + 1].isdigit()
        ):
            score = SCORE_RE.match(lines[i + 3])
            if score:
                rows.append(
                    {
                        "competition": f"{COMPETITION} - {round_name}",
                        "home_team": _clean_team(lines[i + 2]),
                        "away_team": _clean_team(lines[i + 4]),
                        "kickoff_uk": f"{current_date.isoformat()} {line}",
                        "venue": "-",
                        "home_score": int(score.group(1)),
                        "away_score": int(score.group(2)),
                        "official_source": RESULTS_URL,
                    }
                )
            i += 5
            continue

        i += 1

    return build_results_df(rows)


def _round_ids(results_html: str) -> list[tuple[str, str]]:
    """[(round id, round name)] for every proper round on the results page."""
    pairs = re.findall(
        r'class="gTable-title" data="(\d+)"[\s\S]*?<a href="#" title="">([^<]+)</a>', results_html
    )
    return [(rid, name.strip()) for rid, name in pairs if PROPER_ROUND_RE.search(name) and "Qualifying" not in name]


def _html_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


def scrape_womens_fa_cup():
    return parse_fixture_lines(fetch_lines(FIXTURES_URL))


def scrape_womens_fa_cup_results():
    results_html = requests.get(RESULTS_URL, headers=HEADERS, timeout=60).text
    frames = []
    for round_id, round_name in _round_ids(results_html):
        response = requests.post(
            ROUND_RESULTS_URL, data={"roundId": round_id, "page": 0}, headers=HEADERS, timeout=60
        )
        response.raise_for_status()
        frames.append(parse_round_results(_html_lines(response.text), round_name))

    frames = [f for f in frames if not f.empty]
    if not frames:
        return build_results_df([])
    import pandas as pd

    return pd.concat(frames, ignore_index=True)
