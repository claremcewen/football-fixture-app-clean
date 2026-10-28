"""Local daily fixture digest, opened automatically at PC logon.

Writes today's fixtures (grouped by league) to a text file on the Desktop
and opens it. Every day also appends a results round-up: yesterday's
results, or the full weekend (Sat+Sun) on Mondays since that's one natural
block - covers every competition that has results. Originally Monday-only
and limited to a hardcoded competition list, which silently skipped
midweek competitions (UWCL, Subway Players Cup) and SWPL 1 / Adran Premier
/ NWSL entirely. On Fridays it also lists Saturday's and Sunday's fixtures
(one block each) so "games today" posts can be scheduled ahead.

Run with no arguments it writes the daily digest to the Desktop and opens it.
`--weekend` writes just the coming weekend's fixtures (Saturday and Sunday,
one block each) to the Desktop. `--publish` writes data/digest.txt and
data/weekend.txt inside the repo instead (nothing opened) - the scheduled
GitHub Action runs that, so both are readable on a phone from the repo's raw
file links without needing the laptop.
"""
from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "fixtures_all.csv"
RESULTS_FILE = REPO_ROOT / "data" / "results_all.csv"
OUTPUT_FILE = Path.home() / "Desktop" / "Todays_Fixtures.txt"
WEEKEND_OUTPUT_FILE = Path.home() / "Desktop" / "Weekend_Fixtures.txt"
PUBLISHED_DIGEST_FILE = REPO_ROOT / "data" / "digest.txt"
PUBLISHED_WEEKEND_FILE = REPO_ROOT / "data" / "weekend.txt"
LONDON = ZoneInfo("Europe/London")

# Mirrors app.py's COMPETITION_PRIORITY - keeps the same-day league order
# consistent between the app and this digest.
COMPETITION_PRIORITY: dict[str, int] = {
    "WSL": 1,
    "WSL2": 2,
    "Northern Premier Division": 3,
    "Southern Premier Division": 3,
    "Division 1 North": 4,
    "Division 1 Midlands": 4,
    "Division 1 South East": 4,
    "Division 1 South West": 4,
    "FAWNL Cup": 5,
    "Women's FA Cup": 5,
    "England Women": 6,
    "WWC Play-Offs": 6,
    "UWCL": 7,
    "NWSL": 8,
}
DEFAULT_PRIORITY_FALLBACK = 99


def load_fixtures() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(DATA_FILE)
    if df.empty:
        return df
    df["kickoff"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff"]).copy()
    df["date"] = df["kickoff"].dt.date
    return df


def load_results() -> pd.DataFrame:
    if not RESULTS_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(RESULTS_FILE)
    if df.empty:
        return df
    df["kickoff"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff"]).copy()
    df["date"] = df["kickoff"].dt.date
    return df


def watch_text_for(row: pd.Series) -> str:
    """The confirmed broadcaster, or "" - "TBC" / "No broadcast info" are left
    off the digest entirely since they only ever got deleted by hand."""
    watch_platforms = row.get("watch_platforms", "")
    if pd.notna(watch_platforms) and str(watch_platforms).strip():
        return str(watch_platforms)
    return ""


def format_grouped(df: pd.DataFrame) -> str:
    if df.empty:
        return "No fixtures."

    df = df.copy()
    df["_priority"] = df["competition_group"].map(
        lambda c: COMPETITION_PRIORITY.get(c, DEFAULT_PRIORITY_FALLBACK)
    )
    df = df.sort_values(["_priority", "competition_group", "kickoff"])

    lines: list[str] = []
    for group, rows in df.groupby("competition_group", sort=False):
        lines.append(group)
        for _, row in rows.iterrows():
            line = f"{row['home_team']} vs {row['away_team']} - {row['kickoff'].strftime('%H:%M')}"
            watch = watch_text_for(row)
            lines.append(f"{line} - {watch}" if watch else line)
        lines.append("")
    return "\n".join(lines).rstrip()


def format_results_grouped(df: pd.DataFrame) -> str:
    if df.empty:
        return "No results found."

    df = df.copy()
    df["_priority"] = df["competition_group"].map(
        lambda c: COMPETITION_PRIORITY.get(c, DEFAULT_PRIORITY_FALLBACK)
    )
    df = df.sort_values(["_priority", "competition_group", "kickoff"])

    lines: list[str] = []
    for group, rows in df.groupby("competition_group", sort=False):
        lines.append(group)
        for _, row in rows.iterrows():
            lines.append(
                f"{row['home_team']} {row['home_score']:.0f} - {row['away_score']:.0f} {row['away_team']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def _day_blocks(fixtures_df: pd.DataFrame, days: list[datetime.date]) -> list[str]:
    sections: list[str] = []
    for day in days:
        day_fixtures = fixtures_df[fixtures_df["date"] == day] if not fixtures_df.empty else fixtures_df
        sections += [
            "",
            "=" * 40,
            "",
            f"{day.strftime('%A %d %B').upper()} FIXTURES",
            "",
            format_grouped(day_fixtures),
        ]
    return sections


def coming_saturday(today: datetime.date) -> datetime.date:
    """The Saturday of the weekend being planned: the coming one Mon-Fri, or
    this weekend's if today already is Saturday/Sunday."""
    if today.weekday() == 6:
        return today - datetime.timedelta(days=1)
    return today + datetime.timedelta(days=(5 - today.weekday()) % 7)


def build_weekend_fixtures(fixtures_df: pd.DataFrame, today: datetime.date) -> str:
    saturday = coming_saturday(today)
    sunday = saturday + datetime.timedelta(days=1)
    title = f"WEEKEND FIXTURES - {saturday.strftime('%d %b')} & {sunday.strftime('%d %b %Y')}"
    return "\n".join([title] + _day_blocks(fixtures_df, [saturday, sunday]))


def build_digest(fixtures_df: pd.DataFrame, results_df: pd.DataFrame, today: datetime.date) -> str:
    sections: list[str] = [f"TODAY'S FIXTURES - {today.strftime('%A %d %B %Y')}", ""]

    todays = fixtures_df[fixtures_df["date"] == today] if not fixtures_df.empty else fixtures_df
    sections.append(format_grouped(todays))

    if today.weekday() == 4:  # Friday - weekend fixtures, one block per day, for scheduling ahead
        sections += _day_blocks(fixtures_df, [today + datetime.timedelta(days=1), today + datetime.timedelta(days=2)])

    if today.weekday() == 0:  # Monday - the weekend is one natural block
        saturday = today - datetime.timedelta(days=2)
        sunday = today - datetime.timedelta(days=1)
        covered_dates = [saturday, sunday]
        heading = f"WEEKEND ROUND-UP - {saturday.strftime('%a %d %b')} & {sunday.strftime('%a %d %b')}"
    else:
        yesterday = today - datetime.timedelta(days=1)
        covered_dates = [yesterday]
        heading = f"RESULTS ROUND-UP - {yesterday.strftime('%A %d %b')}"

    recent = results_df[results_df["date"].isin(covered_dates)] if not results_df.empty else results_df
    sections += [
        "",
        "=" * 40,
        "",
        heading,
        "",
        format_results_grouped(recent),
    ]

    return "\n".join(sections)


def _write_and_open(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if sys.platform == "win32":
        os.startfile(path)  # noqa: S606 - opens the text file, intentional


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--weekend", action="store_true", help="coming weekend's fixtures only")
    mode.add_argument("--publish", action="store_true", help="write the phone-readable files into data/")
    args = parser.parse_args(argv)

    fixtures_df = load_fixtures()
    results_df = load_results()
    now = datetime.datetime.now(LONDON)
    today = now.date()

    if args.weekend:
        _write_and_open(WEEKEND_OUTPUT_FILE, build_weekend_fixtures(fixtures_df, today))
    elif args.publish:
        stamp = f"Updated {now.strftime('%a %d %b %H:%M')} UK time\n\n"
        PUBLISHED_DIGEST_FILE.write_text(stamp + build_digest(fixtures_df, results_df, today), encoding="utf-8")
        PUBLISHED_WEEKEND_FILE.write_text(stamp + build_weekend_fixtures(fixtures_df, today), encoding="utf-8")
    else:
        _write_and_open(OUTPUT_FILE, build_digest(fixtures_df, results_df, today))


if __name__ == "__main__":
    main()
