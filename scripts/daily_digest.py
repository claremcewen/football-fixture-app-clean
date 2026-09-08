"""Local daily fixture digest, opened automatically at PC logon.

Writes today's fixtures (grouped by league) to a text file on the Desktop
and opens it. On Mondays, also appends a round-up of the weekend just gone
(WSL / WSL2 / FAWNL / knockout cups / England internationals).
"""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "data" / "fixtures_all.csv"
RESULTS_FILE = REPO_ROOT / "data" / "results_all.csv"
OUTPUT_FILE = Path.home() / "Desktop" / "Todays_Fixtures.txt"

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
    "England Women": 6,
    "UWCL": 7,
    "NWSL": 8,
}
DEFAULT_PRIORITY_FALLBACK = 99

# Mirrors app.py's NO_BROADCAST_SOURCE_COMPETITIONS - these sources have no
# broadcaster field at all, so a blank watch_platforms means "No broadcast
# info" here rather than "TBC" (which implies an announcement is coming).
NO_BROADCAST_SOURCE_COMPETITIONS: set[str] = {
    "Northern Premier Division",
    "Southern Premier Division",
    "Division 1 North",
    "Division 1 Midlands",
    "Division 1 South East",
    "Division 1 South West",
    "FAWNL Cup",
    "SWPL 1",
    "Adran Premier",
}

# What counts as "the weekend's action" for the Monday round-up.
WEEKEND_ROUNDUP_GROUPS: set[str] = {
    "WSL",
    "WSL2",
    "Northern Premier Division",
    "Southern Premier Division",
    "Division 1 North",
    "Division 1 Midlands",
    "Division 1 South East",
    "Division 1 South West",
    "FAWNL Cup",
    "Subway Players Cup",
    "England Women",
    "England Women U20",
}


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
    watch_platforms = row.get("watch_platforms", "")
    if pd.notna(watch_platforms) and str(watch_platforms).strip():
        return str(watch_platforms)
    if row.get("competition_group") in NO_BROADCAST_SOURCE_COMPETITIONS:
        return "No broadcast info"
    return "TBC"


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
            lines.append(
                f"{row['home_team']} vs {row['away_team']} - "
                f"{row['kickoff'].strftime('%H:%M')} - {watch_text_for(row)}"
            )
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


def build_digest(fixtures_df: pd.DataFrame, results_df: pd.DataFrame, today: datetime.date) -> str:
    sections: list[str] = [f"TODAY'S FIXTURES - {today.strftime('%A %d %B %Y')}", ""]

    todays = fixtures_df[fixtures_df["date"] == today] if not fixtures_df.empty else fixtures_df
    sections.append(format_grouped(todays))

    if today.weekday() == 0:  # Monday
        saturday = today - datetime.timedelta(days=2)
        sunday = today - datetime.timedelta(days=1)
        weekend = (
            results_df[
                results_df["date"].isin([saturday, sunday])
                & results_df["competition_group"].isin(WEEKEND_ROUNDUP_GROUPS)
            ]
            if not results_df.empty
            else results_df
        )
        sections += [
            "",
            "=" * 40,
            "",
            f"WEEKEND ROUND-UP - {saturday.strftime('%a %d %b')} & {sunday.strftime('%a %d %b')}",
            "(WSL / WSL2 / FAWNL / knockout cups / England internationals)",
            "",
            format_results_grouped(weekend),
        ]

    return "\n".join(sections)


def main() -> None:
    fixtures_df = load_fixtures()
    results_df = load_results()
    today = datetime.date.today()
    digest = build_digest(fixtures_df, results_df, today)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(digest, encoding="utf-8")

    if sys.platform == "win32":
        os.startfile(OUTPUT_FILE)  # noqa: S606 - opens the text file, intentional


if __name__ == "__main__":
    main()
