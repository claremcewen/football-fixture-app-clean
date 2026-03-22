
from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.scrapers.internationals import scrape_england_women
from scripts.scrapers.wsl import scrape_wsl
from scripts.scrapers.wsl2 import scrape_wsl2
from scripts.scrapers.uwcl import scrape_uwcl

OUTPUT_FILE = ROOT_DIR / "data" / "fixtures_all.csv"


def combine_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if frame is not None and not frame.empty]
    if not non_empty:
        return pd.DataFrame(
            columns=[
                "competition",
                "home_team",
                "away_team",
                "kickoff_uk",
                "venue",
                "watch_platforms",
                "watch_notes",
                "official_source",
            ]
        )

    combined = pd.concat(non_empty, ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["competition", "home_team", "away_team", "kickoff_uk", "venue"]
    ).copy()
    combined["kickoff_uk"] = pd.to_datetime(combined["kickoff_uk"], errors="coerce")
    combined = combined.dropna(subset=["kickoff_uk"]).sort_values("kickoff_uk")
    combined["kickoff_uk"] = combined["kickoff_uk"].dt.strftime("%Y-%m-%d %H:%M")
    return combined.reset_index(drop=True)


def main() -> None:
    print("Updating fixtures...")
    frames = []

    tasks = [
        ("WSL", scrape_wsl),
        ("WSL2", scrape_wsl2),
        ("England Women", scrape_england_women),
         ("UWCL", scrape_uwcl),
    ]

    for label, func in tasks:
        try:
            df = func()
            frames.append(df)
            print(f"\n✓ {label}: {len(df)} fixtures")

            if df is None:
                print(f"{label} returned None")
            elif df.empty:
                print(f"{label} returned an empty dataframe")
            else:
                print(f"{label} columns: {list(df.columns)}")
                print(df.head(5).to_string(index=False))

        except Exception as exc:
            print(f"\n✗ {label}: {exc}")

    combined = combine_frames(frames)

    print("\nCombined dataframe preview:")
    if combined.empty:
        print("Combined dataframe is empty")
    else:
        print(combined.head(10).to_string(index=False))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {len(combined)} fixtures to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
