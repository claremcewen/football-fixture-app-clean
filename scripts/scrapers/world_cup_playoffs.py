from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .common import (
    build_df,
    build_live_football_on_tv_broadcast_lookup,
    build_results_df,
    fetch_html,
    _normalise_team_for_matching,
    to_uk_iso_from_tz,
)

# UEFA's play-offs for the 2027 Women's World Cup - 16 two-legged ties on
# 9 and 13 Oct 2026, then a second round in Nov/Dec. Wikipedia's article
# lists every tie in the same "footballbox" template the UWCL scraper reads.
# Bump the URL for the next World Cup cycle.
PLAYOFFS_URL = (
    "https://en.wikipedia.org/wiki/"
    "2027_FIFA_Women%27s_World_Cup_qualification_%E2%80%93_UEFA_play-offs"
)
COMPETITION = "FIFA Women's World Cup 2027 Play-Off"

# Unparenthesised times on these pages are UEFA's own listed time (CET/CEST),
# same convention as the UWCL pages - converted to UK time from Europe/Paris.
UEFA_LISTED_TZ = "Europe/Paris"

# England's ties already come from englandfootball.com (richer: venue
# detail, broadcaster) - skipped here so they don't appear twice.
EXCLUDED_TEAM = "England"

# live-footballontv.com's tags for these ties, one per leg. It only lists
# matches with a UK broadcaster, so it's a fallback for the broadcaster
# column only.
LIVE_FOOTBALL_ON_TV_TAGS = (
    "FIFA Women's World Cup 2027 Play-Off 1st Leg",
    "FIFA Women's World Cup 2027 Play-Off 2nd Leg",
)

SCORE_RE = re.compile(r"(\d+)\s*[–-]\s*(\d+)")
TIME_RE = re.compile(r"^(\d{1,2}:\d{2})")


def _parse_ties(html: str) -> list[dict]:
    """Every tie with real teams and a full date (the second-round boxes only
    show "Winner Tie 11" and a month until the first round resolves - skipped
    until they become real fixtures)."""
    soup = BeautifulSoup(html, "html.parser")
    ties = []

    for box in soup.find_all("div", class_="footballbox"):
        home = box.select_one("th.fhome span[itemprop=name]")
        away = box.select_one("th.faway span[itemprop=name]")
        score_el = box.select_one("th.fscore")
        date_el = box.select_one(".fdate .bday")
        time_el = box.select_one(".ftime")
        if not (home and away and score_el and date_el and time_el):
            continue

        home_name = home.get_text(" ", strip=True)
        away_name = away.get_text(" ", strip=True)
        if home_name.startswith("Winner") or away_name.startswith("Winner"):
            continue
        if EXCLUDED_TEAM in (home_name, away_name):
            continue

        try:
            match_date = datetime.strptime(date_el.get_text(strip=True), "%Y-%m-%d").date()
        except ValueError:
            continue
        time_match = TIME_RE.match(time_el.get_text(strip=True))
        if not time_match:
            continue

        venue_el = box.select_one(".fright [itemprop=location] [itemprop=name]")
        score_match = SCORE_RE.search(score_el.get_text(" ", strip=True))

        ties.append(
            {
                "home_team": home_name,
                "away_team": away_name,
                "match_date": match_date,
                "kickoff_uk": to_uk_iso_from_tz(match_date, time_match.group(1), UEFA_LISTED_TZ),
                "venue": venue_el.get_text(" ", strip=True) if venue_el else "-",
                "score": (int(score_match.group(1)), int(score_match.group(2))) if score_match else None,
            }
        )

    return ties


def parse_playoff_fixtures(html: str, broadcast_lookup: dict | None = None):
    broadcast_lookup = broadcast_lookup or {}
    rows = []
    for tie in _parse_ties(html):
        if tie["score"] is not None:
            continue
        key = (
            tie["match_date"],
            _normalise_team_for_matching(tie["home_team"]),
            _normalise_team_for_matching(tie["away_team"]),
        )
        rows.append(
            {
                "competition": COMPETITION,
                "home_team": tie["home_team"],
                "away_team": tie["away_team"],
                "kickoff_uk": tie["kickoff_uk"],
                "venue": tie["venue"],
                "watch_platforms": broadcast_lookup.get(key, ""),
                "watch_notes": "",
                "official_source": PLAYOFFS_URL,
            }
        )
    return build_df(rows)


def parse_playoff_results(html: str):
    rows = []
    for tie in _parse_ties(html):
        if tie["score"] is None:
            continue
        rows.append(
            {
                "competition": COMPETITION,
                "home_team": tie["home_team"],
                "away_team": tie["away_team"],
                "kickoff_uk": tie["kickoff_uk"],
                "venue": tie["venue"],
                "home_score": tie["score"][0],
                "away_score": tie["score"][1],
                "official_source": PLAYOFFS_URL,
            }
        )
    return build_results_df(rows)


def scrape_world_cup_playoffs():
    broadcast_lookup: dict = {}
    for tag in LIVE_FOOTBALL_ON_TV_TAGS:
        broadcast_lookup.update(build_live_football_on_tv_broadcast_lookup(tag))
    return parse_playoff_fixtures(fetch_html(PLAYOFFS_URL), broadcast_lookup)


def scrape_world_cup_playoffs_results():
    return parse_playoff_results(fetch_html(PLAYOFFS_URL))
