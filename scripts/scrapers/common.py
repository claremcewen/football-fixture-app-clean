
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

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

def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


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


def build_df(rows: Iterable[dict]) -> pd.DataFrame:
    columns = [
        "competition",
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
