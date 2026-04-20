from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "data" / "fixtures_all.csv"

st.set_page_config(
    page_title="Women's Football Watch Guide",
    page_icon="⚽",
    layout="wide",
)


def simplify_competition_label(label: str) -> str:
    label = str(label).strip()

    if "UEFA Women's Champions League" in label:
        return "UWCL"
    if label.startswith("England Women"):
        return "England Women"
    if "WSL2" in label:
        return "WSL2"
    if "WSL" in label:
        return "WSL"

    return label


def get_weekend_range(today_date):
    weekday = today_date.weekday()  # Monday=0, Sunday=6

    if weekday < 5:  # Mon-Fri
        days_until_sat = 5 - weekday
        start_date = today_date + timedelta(days=days_until_sat)
        end_date = start_date + timedelta(days=1)
    elif weekday == 5:  # Saturday
        start_date = today_date
        end_date = today_date + timedelta(days=1)
    else:  # Sunday
        start_date = today_date
        end_date = today_date

    return start_date, end_date


@st.cache_data
def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame(
            columns=[
                "competition",
                "competition_group",
                "home_team",
                "away_team",
                "kickoff_uk",
                "venue",
                "watch_platforms",
                "watch_notes",
                "official_source",
            ]
        )

    df = pd.read_csv(DATA_FILE)

    if df.empty:
        return df

    # Clean fields so 'nan' doesn't show in the UI
    for col in ["venue", "watch_platforms", "watch_notes", "official_source"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).replace("nan", "").replace("NaT", "")

    df["kickoff"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff"]).copy()
    df["date"] = df["kickoff"].dt.date
    df["time"] = df["kickoff"].dt.strftime("%H:%M")
    df["display_date"] = (
        df["kickoff"].dt.strftime("%A")
        + " "
        + df["kickoff"].dt.day.astype(str)
        + " "
        + df["kickoff"].dt.strftime("%B %Y")
    )
    df["competition_group"] = df["competition"].apply(simplify_competition_label)

    return df.sort_values("kickoff").reset_index(drop=True)


def filter_data(
    df: pd.DataFrame,
    competition: str,
    platform: str,
    club: str,
    free_only: bool,
    view_mode: str,
    selected_date=None,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    filtered = df.copy()

    if view_mode == "single" and selected_date is not None:
        filtered = filtered[filtered["date"] == selected_date]
    elif view_mode == "range" and start_date is not None and end_date is not None:
        filtered = filtered[
            (filtered["date"] >= start_date) & (filtered["date"] <= end_date)
        ]
    elif view_mode == "all":
        pass

    if competition != "All":
        filtered = filtered[filtered["competition_group"] == competition]

    if platform != "All":
        filtered = filtered[
            filtered["watch_platforms"].str.contains(platform, case=False, na=False)
        ]

    if club != "All":
        filtered = filtered[
            (filtered["home_team"] == club) | (filtered["away_team"] == club)
        ]

    if free_only:
        filtered = filtered[
            filtered["watch_platforms"].str.contains(
                "BBC|YouTube|BBC iPlayer|BBC Sport Website|ITV",
                case=False,
                na=False,
            )
        ]

    return filtered.sort_values("kickoff")


def match_card(row: pd.Series) -> None:
    with st.container(border=True):
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader(f"{row['home_team']} vs {row['away_team']}")
            st.write(f"**Competition:** {row['competition']}")

            kickoff = row["kickoff"]
            pretty_kickoff = (
                f"{kickoff.strftime('%A')} {kickoff.day} "
                f"{kickoff.strftime('%B')}, {kickoff.strftime('%H:%M')}"
            )
            st.write(f"**Kick-off (UK):** {pretty_kickoff}")
            st.write(f"**Venue:** {row.get('venue', 'TBC') or 'TBC'}")

        with col2:
            watch_platforms = row.get("watch_platforms", "")
            watch_platforms = str(watch_platforms).strip()
            st.write(f"**Watch:** {watch_platforms if watch_platforms else 'TBC'}")

            notes = row.get("watch_notes", "")
            if pd.notna(notes) and str(notes).strip():
                st.write(f"**Notes:** {notes}")

            source = row.get("official_source", "")
            if pd.notna(source) and str(source).strip():
                st.link_button("Official fixture source", source)


def make_download(df: pd.DataFrame) -> None:
    download_df = df[
        [
            "competition",
            "home_team",
            "away_team",
            "kickoff_uk",
            "venue",
            "watch_platforms",
            "watch_notes",
            "official_source",
        ]
    ].copy()

    st.download_button(
        label="Download filtered fixtures as CSV",
        data=download_df.to_csv(index=False).encode("utf-8"),
        file_name="womens-football-watch-guide.csv",
        mime="text/csv",
    )


def format_pretty_date(date_value) -> str:
    ts = pd.Timestamp(date_value)
    return f"{ts.strftime('%A')} {ts.day} {ts.strftime('%B %Y')}"


def main() -> None:
    df = load_data()

    st.title("⚽ Women's Football Watch Guide")
    st.caption(
        "Phase 2 starter: WSL, WSL2, England Women and UWCL from generated combined data."
    )

    if df.empty:
        st.warning(
            "No fixture data found yet. Run `python scripts/update_fixtures.py` first, "
            "then refresh this app."
        )
        return

    now = pd.Timestamp.now()
    if getattr(now, "tzinfo", None) is not None:
        now = now.tz_localize(None)

    today_date = pd.Timestamp.today().date()

    upcoming = df[df["kickoff"] >= now]
    next_match = upcoming.iloc[0] if not upcoming.empty else df.iloc[0]

    top1, top2, top3 = st.columns(3)
    with top1:
        st.metric("Matches loaded", len(df))
    with top2:
        st.metric("Competitions", df["competition"].nunique())
    with top3:
        st.metric("Next match", f"{next_match['home_team']} vs {next_match['away_team']}")

    st.divider()

    unique_dates = sorted(df["date"].unique())
    min_fixture_date = min(unique_dates)
    max_fixture_date = max(unique_dates)

    competitions = ["All"] + sorted(df["competition_group"].dropna().unique().tolist())
    clubs = ["All"] + sorted(pd.unique(pd.concat([df["home_team"], df["away_team"]])).tolist())
    platforms = ["All"] + sorted(
        {
            p.strip()
            for cell in df["watch_platforms"].dropna()
            for p in str(cell).split(",")
            if p.strip()
        }
    )

    # Allow today to be selected even if fixtures start later
    widget_min_date = min(today_date, min_fixture_date)

    # Session state defaults
    if "selected_date_state" not in st.session_state:
        st.session_state["selected_date_state"] = today_date
    if "view_mode_state" not in st.session_state:
        st.session_state["view_mode_state"] = "single"
    if "range_start_state" not in st.session_state:
        st.session_state["range_start_state"] = today_date
    if "range_end_state" not in st.session_state:
        st.session_state["range_end_state"] = today_date + pd.Timedelta(days=6)
    if "competition_main" not in st.session_state:
        st.session_state["competition_main"] = "All"
    if "platform_main" not in st.session_state:
        st.session_state["platform_main"] = "All"
    if "club_main" not in st.session_state:
        st.session_state["club_main"] = "All"
    if "free_only_filter" not in st.session_state:
        st.session_state["free_only_filter"] = False

    # Keep stored dates within sensible bounds
    if st.session_state["selected_date_state"] > max_fixture_date:
        st.session_state["selected_date_state"] = max_fixture_date

    if st.session_state["range_start_state"] > max_fixture_date:
        st.session_state["range_start_state"] = today_date

    if st.session_state["range_end_state"] > max_fixture_date:
        st.session_state["range_end_state"] = min(
            today_date + pd.Timedelta(days=6), max_fixture_date
        )

    # Reset button
    if st.button("Reset filters", key="reset_filters"):
        st.session_state["competition_main"] = "All"
        st.session_state["platform_main"] = "All"
        st.session_state["club_main"] = "All"
        st.session_state["free_only_filter"] = False
        st.session_state["view_mode_state"] = "single"
        st.session_state["selected_date_state"] = today_date
        st.session_state["range_start_state"] = today_date
        st.session_state["range_end_state"] = min(
            today_date + pd.Timedelta(days=6), max_fixture_date
        )
        st.rerun()

    # Main filters
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        selected_date = st.date_input(
            "Date",
            value=st.session_state["selected_date_state"],
            min_value=widget_min_date,
            max_value=max_fixture_date,
            key="date_input_main",
        )

        if selected_date != st.session_state["selected_date_state"]:
            st.session_state["view_mode_state"] = "single"

        st.session_state["selected_date_state"] = selected_date

    with c2:
        competition = st.selectbox("Competition", competitions, key="competition_main")

    with c3:
        platform = st.selectbox("Watch platform", platforms, key="platform_main")

    with c4:
        club = st.selectbox("Club", clubs, key="club_main")

    free_only = st.checkbox(
        "Show free-to-watch matches only (BBC / YouTube / ITV)",
        key="free_only_filter",
    )

    # Quick buttons
    quick1, quick2, quick3, quick4 = st.columns(4)

    with quick1:
        if st.button("Today", key="quick_today"):
            st.session_state["view_mode_state"] = "single"
            st.session_state["selected_date_state"] = today_date
            st.rerun()

    with quick2:
        if st.button("Weekend", key="quick_weekend"):
            weekend_start, weekend_end = get_weekend_range(today_date)
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = weekend_start
            st.session_state["range_end_state"] = min(weekend_end, max_fixture_date)
            st.rerun()

    with quick3:
        if st.button("Next 7 Days", key="quick_next_7_days"):
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = today_date
            st.session_state["range_end_state"] = min(
                today_date + pd.Timedelta(days=6), max_fixture_date
            )
            st.rerun()

    with quick4:
        if st.button("Full Fixture List", key="quick_full_fixture_list"):
            st.session_state["view_mode_state"] = "all"
            st.rerun()

    view_mode = st.session_state["view_mode_state"]
    selected_date = st.session_state["selected_date_state"]
    range_start = st.session_state["range_start_state"]
    range_end = st.session_state["range_end_state"]

    filtered = filter_data(
        df,
        competition,
        platform,
        club,
        free_only,
        view_mode=view_mode,
        selected_date=selected_date,
        start_date=range_start,
        end_date=range_end,
    )

    if view_mode == "single":
        pretty_date = format_pretty_date(selected_date)
        st.info(f"Showing fixtures for {pretty_date}.")
    elif view_mode == "range":
        pretty_start = format_pretty_date(range_start)
        pretty_end = format_pretty_date(range_end)
        st.info(f"Showing fixtures from {pretty_start} to {pretty_end}.")
    else:
        st.info("Showing full fixture list.")

    if view_mode == "single" and selected_date == today_date:
        st.success("Today's matches ⚽")

    st.divider()

    # Special case: no games today -> say so, show next fixture date, then next 7 days below
    if view_mode == "single" and selected_date == today_date and filtered.empty:
        st.warning(f"No fixtures today ({format_pretty_date(today_date)}).")

        next_fixtures_all = df[df["date"] > today_date].sort_values("kickoff")
        if not next_fixtures_all.empty:
            next_fixture_date = next_fixtures_all.iloc[0]["date"]
            st.info(f"Next fixture date: {format_pretty_date(next_fixture_date)}")
        else:
            st.info("There are no upcoming fixtures in the current dataset.")

        next_7_days = filter_data(
            df,
            competition,
            platform,
            club,
            free_only,
            view_mode="range",
            start_date=today_date,
            end_date=min(today_date + pd.Timedelta(days=6), max_fixture_date),
        )

        if next_7_days.empty:
            st.info("No fixtures in the next 7 days.")
        else:
            st.write("### Fixtures in the next 7 days")

            current_group_date = None
            for _, row in next_7_days.iterrows():
                row_date = row["date"]

                if row_date != current_group_date:
                    st.markdown(f"## {format_pretty_date(row_date)}")
                    current_group_date = row_date

                match_card(row)

            make_download(next_7_days)

    elif filtered.empty:
        st.warning("No matches found for those filters.")

    else:
        if view_mode == "single":
            st.write(f"### {len(filtered)} match(es) on {pretty_date}")
        elif view_mode == "range":
            st.write(f"### {len(filtered)} match(es) in this date range")
        else:
            st.write(f"### {len(filtered)} match(es) in the full fixture list")

        current_group_date = None

        for _, row in filtered.iterrows():
            row_date = row["date"]

            if row_date != current_group_date:
                st.markdown(f"## {format_pretty_date(row_date)}")
                current_group_date = row_date

            match_card(row)

        make_download(filtered)

    st.divider()

    with st.expander("All loaded fixtures"):
        table_df = df[
            [
                "competition",
                "home_team",
                "away_team",
                "kickoff_uk",
                "venue",
                "watch_platforms",
            ]
        ].copy()
        st.dataframe(table_df, width="stretch", hide_index=True)

    with st.expander("How to update this Phase 2 starter"):
        st.markdown(
            """
- Run `python scripts/update_fixtures.py` to regenerate `data/fixtures_all.csv`.
- The combined file is built from WSL, WSL2, England Women and UWCL sources.
- Next recommended step: add a GitHub Actions scheduled workflow and deploy to Streamlit Community Cloud.
"""
        )


if __name__ == "__main__":
    main()