from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.registry import classify
from scripts.scrapers.england_u20_women import scrape_england_u20_women
from scripts.scrapers.fawnl import scrape_fawnl
from scripts.scrapers.internationals import scrape_england_women
from scripts.scrapers.nwsl import scrape_nwsl
from scripts.scrapers.players_cup import scrape_players_cup
from scripts.scrapers.swpl import scrape_swpl
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
    "tier",
    "home_team",
    "away_team",
    "kickoff_uk",
    "venue",
    "watch_platforms",
    "watch_notes",
    "official_source",
]

# A same-day drop this steep basically never happens for a legitimate
# reason - real fixture counts decline gradually as matches are played, not
# in cliffs. Wired up after wslfootball.com was twice observed serving a
# genuinely partial fixture list (10 rows instead of ~175) without ever
# returning zero, which the plain zero-rows check below doesn't catch.
# Only applied once the previous count is large enough that a drop this
# steep is meaningful - guards against noise on already-small competitions
# (e.g. England Women's 2 fixtures) where any change looks "drastic".
SUSPICIOUS_DROP_RATIO = 0.5
SUSPICIOUS_DROP_MIN_PREVIOUS = 15


def is_suspicious_drop(row_count: int, previous_count: int) -> bool:
    return (
        previous_count >= SUSPICIOUS_DROP_MIN_PREVIOUS
        and row_count < previous_count * SUSPICIOUS_DROP_RATIO
    )

FAWNL_DIVISIONS = [
    "Northern Premier Division",
    "Southern Premier Division",
    "Division 1 North",
    "Division 1 Midlands",
    "Division 1 South East",
    "Division 1 South West",
    "FAWNL Cup",
]

# (task label, scraper function, competition_group values it can produce).
# Most scrapers cover exactly one competition_group; FAWNL's single API call
# covers six divisions at once, so it needs the full list for fallback
# matching below.
TASKS = [
    ("WSL", scrape_wsl, ["WSL"]),
    ("WSL2", scrape_wsl2, ["WSL2"]),
    ("England Women", scrape_england_women, ["England Women"]),
    ("England Women U20", scrape_england_u20_women, ["England Women U20"]),
    ("UWCL", scrape_uwcl, ["UWCL"]),
    ("NWSL", scrape_nwsl, ["NWSL"]),
    ("FAWNL", scrape_fawnl, FAWNL_DIVISIONS),
    # WAFCON unplugged for now - the 2025 edition is over. scrapers/wafcon.py
    # and its tests are left in place (dormant) so the next edition is a
    # quick resume, not a from-scratch source investigation.
    ("SWPL 1", scrape_swpl, ["SWPL 1"]),
    ("Subway Players Cup", scrape_players_cup, ["Subway Players Cup"]),
]


def classify_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Populate sport/competition_group/region/tier from the raw competition label.

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
    df["tier"] = classified.apply(lambda c: c[3])
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


def previous_rows_for(group_labels: list[str], previous_df: pd.DataFrame) -> pd.DataFrame:
    if previous_df.empty or "competition_group" not in previous_df.columns:
        return pd.DataFrame(columns=COLUMNS)
    return previous_df[previous_df["competition_group"].isin(group_labels)].copy()


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

    frames: list[pd.DataFrame] = []
    status: dict[str, dict] = {}

    for label, func, group_labels in TASKS:
        fallback = previous_rows_for(group_labels, previous_df)

        try:
            df = clean_frame(classify_frame(func()))
            row_count = len(df)

            suspicious_drop = is_suspicious_drop(row_count, len(fallback))

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
            elif suspicious_drop:
                print(
                    f"[WARN] {label}: scraper returned {row_count} rows, a sharp drop "
                    f"from {len(fallback)} previous - keeping previous fixture(s) "
                    "(probable partial/broken source page, not a real decline)"
                )
                frames.append(clean_frame(fallback))
                status[label] = {
                    "ok": False,
                    "rows": len(fallback),
                    "note": (
                        f"scraper returned {row_count} rows, a >{int(SUSPICIOUS_DROP_RATIO * 100)}% "
                        f"drop from {len(fallback)} previous; treated as a probable partial/broken "
                        "scrape and kept previous data"
                    ),
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
