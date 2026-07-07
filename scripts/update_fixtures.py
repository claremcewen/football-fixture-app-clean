from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.registry import classify
from scripts.scrapers.internationals import scrape_england_women
from scripts.scrapers.uwcl import scrape_uwcl
from scripts.scrapers.wsl import scrape_wsl
from scripts.scrapers.wsl2 import scrape_wsl2

OUTPUT_FILE = ROOT_DIR / "data" / "fixtures_all.csv"
STATUS_FILE = ROOT_DIR / "data" / "last_update_status.json"

COLUMNS = [
    "competition",
    "sport",
    "competition_group",
    "region",
    "home_team",
    "away_team",
    "kickoff_uk",
    "venue",
    "watch_platforms",
    "watch_notes",
    "official_source",
]


def classify_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Populate sport/competition_group/region from the raw competition label.

    Always recomputed (not just filled if missing) so this stays valid for
    frames loaded from an older CSV that predates these columns.
    """
    if df.empty:
        return df

    df = df.copy()
    classified = df["competition"].apply(classify)
    df["sport"] = classified.apply(lambda c: c[0])
    df["competition_group"] = classified.apply(lambda c: c[1])
    df["region"] = classified.apply(lambda c: c[2])
    return df


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Drop unparseable/past fixtures and normalise kickoff_uk formatting."""
    if df.empty:
        return df

    df = df.copy()
    df["kickoff_uk"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff_uk"]).copy()

    today_floor = pd.Timestamp.today().normalize()
    df = df[df["kickoff_uk"] >= today_floor].copy()

    df["kickoff_uk"] = df["kickoff_uk"].dt.strftime("%Y-%m-%d %H:%M")
    return df


def load_previous() -> pd.DataFrame:
    if not OUTPUT_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)

    try:
        df = pd.read_csv(OUTPUT_FILE)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

    return classify_frame(df)


def previous_rows_for(group_label: str, previous_df: pd.DataFrame) -> pd.DataFrame:
    if previous_df.empty or "competition_group" not in previous_df.columns:
        return pd.DataFrame(columns=COLUMNS)
    return previous_df[previous_df["competition_group"] == group_label].copy()


def finalize(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]

    if not non_empty:
        return pd.DataFrame(columns=COLUMNS)

    combined = pd.concat(non_empty, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["competition", "home_team", "away_team", "kickoff_uk", "venue"]
    ).copy()
    combined = combined.sort_values("kickoff_uk")
    return combined[COLUMNS].reset_index(drop=True)


def main() -> None:
    print("Updating fixtures...")

    previous_df = load_previous()

    tasks = [
        ("WSL", scrape_wsl),
        ("WSL2", scrape_wsl2),
        ("England Women", scrape_england_women),
        ("UWCL", scrape_uwcl),
    ]

    frames: list[pd.DataFrame] = []
    status: dict[str, dict] = {}

    for label, func in tasks:
        fallback = previous_rows_for(label, previous_df)

        try:
            df = clean_frame(classify_frame(func()))
            row_count = len(df)

            if row_count == 0 and not fallback.empty:
                print(
                    f"[WARN] {label}: scraper returned 0 rows, "
                    f"keeping {len(fallback)} previous fixture(s)"
                )
                frames.append(clean_frame(fallback))
                status[label] = {
                    "ok": False,
                    "rows": len(fallback),
                    "note": "scraper returned 0 rows; fell back to previous data",
                }
            else:
                frames.append(df)
                status[label] = {"ok": True, "rows": row_count}
                print(f"[OK] {label}: {row_count} fixtures")

        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            frames.append(clean_frame(fallback))
            status[label] = {
                "ok": False,
                "rows": len(fallback),
                "note": f"scraper raised: {exc}",
            }

    combined = finalize(frames)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)

    STATUS_FILE.write_text(json.dumps(status, indent=2))

    print(f"\nSaved {len(combined)} fixtures to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
