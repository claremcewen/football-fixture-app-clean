from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.registry import classify
from scripts.scrapers.common import build_results_df
from scripts.scrapers.adran_premier import scrape_adran_premier_results
from scripts.scrapers.england_u20_women import scrape_england_u20_women_results
from scripts.scrapers.fawnl import scrape_fawnl_results
from scripts.scrapers.internationals import scrape_england_women_results
from scripts.scrapers.nwsl import COMPETITION as NWSL_COMPETITION, NWSL_RESULTS_URL, scrape_nwsl_grid_scores
from scripts.scrapers.swpl import scrape_swpl_results
from scripts.scrapers.uwcl import scrape_uwcl_results
from scripts.scrapers.wsl import COMPETITION as WSL_COMPETITION, WSL_RESULTS_URL, scrape_wsl_grid_scores
from scripts.scrapers.wsl2 import COMPETITION as WSL2_COMPETITION, WSL2_RESULTS_URL, scrape_wsl2_grid_scores
from scripts.update_fixtures import FIXTURE_DATE_ARCHIVE_FILE

OUTPUT_FILE = ROOT_DIR / "data" / "results_all.csv"
STATUS_FILE = ROOT_DIR / "data" / "last_results_update_status.json"

COLUMNS = [
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

# Natural key for a match, used to dedupe when merging a fresh scrape (which
# only covers a recent window) into the full growing archive.
KEY_COLUMNS = ["competition_group", "home_team", "away_team", "kickoff_uk"]

# Unlike fixtures (a rolling forward-only window), results are meant to
# accumulate forever - each source is only asked for a recent window (see
# each scraper's own RESULTS_WINDOW_DAYS), and this script's job is to keep
# folding that window into the permanent archive already on disk, not to
# replace it.
#
# Subway Players Cup still needs a headless browser (its scores only render
# client-side) or a reverse-engineered private API, AND it has no Wikipedia
# results coverage either (checked - the "FA Women's League Cup" article is
# a history/finals page, no per-season match log) - a deliberately separate
# follow-up, not attempted here.
TASKS = [
    ("SWPL 1", scrape_swpl_results, ["SWPL 1"]),
    ("FAWNL", scrape_fawnl_results, [
        "Northern Premier Division",
        "Southern Premier Division",
        "Division 1 North",
        "Division 1 Midlands",
        "Division 1 South East",
        "Division 1 South West",
        "FAWNL Cup",
    ]),
    ("Adran Premier", scrape_adran_premier_results, ["Adran Premier"]),
    ("England Women", scrape_england_women_results, ["England Women"]),
    ("England Women U20", scrape_england_u20_women_results, ["England Women U20"]),
    ("UWCL", scrape_uwcl_results, ["UWCL"]),
]

# WSL, WSL2 and NWSL results come from a Wikipedia results grid that only
# has a score, never a date, once a match is played - see
# scripts/scrapers/common.py's parse_wikipedia_results_grid docstring. Each
# entry here is (label, grid-scores scraper, competition display name,
# competition_group, source url) - resolved against FIXTURE_DATE_ARCHIVE_FILE
# (this project's own record of when each fixture was originally scheduled,
# captured daily before update_fixtures.py's forward-only file loses it).
GRID_TASKS = [
    ("WSL", scrape_wsl_grid_scores, WSL_COMPETITION, "WSL", WSL_RESULTS_URL),
    ("WSL2", scrape_wsl2_grid_scores, WSL2_COMPETITION, "WSL2", WSL2_RESULTS_URL),
    ("NWSL", scrape_nwsl_grid_scores, NWSL_COMPETITION, "NWSL", NWSL_RESULTS_URL),
]


def classify_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    classified = df["competition"].apply(classify)
    df["sport"] = classified.apply(lambda c: c[0])
    df["competition_group"] = classified.apply(lambda c: c[1])
    df["region"] = classified.apply(lambda c: c[2])
    df["tier"] = classified.apply(lambda c: c[3])
    return df


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["kickoff_uk"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff_uk"]).copy()
    df["kickoff_uk"] = df["kickoff_uk"].dt.strftime("%Y-%m-%d %H:%M")
    return df


def load_archive() -> pd.DataFrame:
    if not OUTPUT_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(OUTPUT_FILE)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

    return classify_frame(df)


def merge_into_archive(archive: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([archive, fresh], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(columns=COLUMNS)

    # keep="last" so a fresh scrape's version of a match (e.g. a corrected
    # score) overrides whatever's already archived for that same match.
    combined = combined.drop_duplicates(subset=KEY_COLUMNS, keep="last")
    combined = combined.sort_values("kickoff_uk")
    return combined[COLUMNS].reset_index(drop=True)


def load_fixture_date_lookup() -> dict[tuple[str, str, str], str]:
    if not FIXTURE_DATE_ARCHIVE_FILE.exists():
        return {}
    df = pd.read_csv(FIXTURE_DATE_ARCHIVE_FILE)
    return {
        (row["competition_group"], row["home_team"], row["away_team"]): row["kickoff_uk"]
        for _, row in df.iterrows()
    }


def resolve_grid_scores(
    grid_scores: list[dict],
    competition: str,
    competition_group: str,
    source_url: str,
    date_lookup: dict[tuple[str, str, str], str],
) -> tuple[pd.DataFrame, int]:
    """Pairs each {home_team, away_team, home_score, away_score} entry from
    a Wikipedia results grid with its real kickoff date, looked up by
    (competition_group, home_team, away_team). A miss just means this
    project's own fixture-date archive hasn't seen that match yet (e.g. it
    was played before this archive started being kept) - skipped rather
    than guessed, and it'll resolve on its own once the archive catches up.
    """
    rows = []
    skipped = 0

    for entry in grid_scores:
        key = (competition_group, entry["home_team"], entry["away_team"])
        kickoff_uk = date_lookup.get(key)
        if not kickoff_uk:
            skipped += 1
            continue

        rows.append(
            {
                "competition": competition,
                "home_team": entry["home_team"],
                "away_team": entry["away_team"],
                "kickoff_uk": kickoff_uk,
                "venue": "-",
                "home_score": entry["home_score"],
                "away_score": entry["away_score"],
                "official_source": source_url,
            }
        )

    return build_results_df(rows), skipped


def main() -> None:
    print("Updating results...")

    archive = load_archive()
    status: dict[str, dict] = {}
    fresh_frames: list[pd.DataFrame] = []

    for label, func, _group_labels in TASKS:
        try:
            df = clean_frame(classify_frame(func()))
            fresh_frames.append(df)
            status[label] = {"ok": True, "rows": len(df)}
            print(f"[OK] {label}: {len(df)} results")
        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            status[label] = {"ok": False, "rows": 0, "note": f"scraper raised: {exc}"}

    date_lookup = load_fixture_date_lookup()
    for label, func, competition, competition_group, source_url in GRID_TASKS:
        try:
            grid_scores = func()
            df, skipped = resolve_grid_scores(grid_scores, competition, competition_group, source_url, date_lookup)
            df = clean_frame(classify_frame(df))
            fresh_frames.append(df)
            status[label] = {"ok": True, "rows": len(df), "note": f"{skipped} score(s) skipped, no known date yet"}
            print(f"[OK] {label}: {len(df)} results ({skipped} skipped, no known date yet)")
        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            status[label] = {"ok": False, "rows": 0, "note": f"scraper raised: {exc}"}

    fresh = pd.concat(fresh_frames, ignore_index=True) if fresh_frames else pd.DataFrame(columns=COLUMNS)
    combined = merge_into_archive(archive, fresh)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)

    STATUS_FILE.write_text(json.dumps(status, indent=2))

    print(f"\nArchive now has {len(combined)} results, saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
