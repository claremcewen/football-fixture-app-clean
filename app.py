from __future__ import annotations

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


def get_next_available_date(target_date, available_dates):
    future_dates = [d for d in available_dates if d >= target_date]
    if future_dates:
        return min(future_dates)
    return available_dates[-1]


def get_next_weekend_date(today, available_dates):
    days_until_next_saturday = ((5 - today.weekday()) % 7) or 7
    next_saturday = today + pd.Timedelta(days=days_until_next_saturday)
    return get_next_available_date(next_saturday, available_dates)


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
            st.write(
                f"**Watch:** {watch_platforms if str(watch_platforms).strip() else 'TBC'}"
            )

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

    # Session state defaults
    if "selected_date_state" not in st.session_state:
        st.session_state["selected_date_state"] = unique_dates[0]

    if "view_mode_state" not in st.session_state:
        st.session_state["view_mode_state"] = "single"

    if "range_start_state" not in st.session_state:
        st.session_state["range_start_state"] = unique_dates[0]

    if "range_end_state" not in st.session_state:
        st.session_state["range_end_state"] = unique_dates[0]

    if "competition_main" not in st.session_state:
        st.session_state["competition_main"] = "All"

    if "platform_main" not in st.session_state:
        st.session_state["platform_main"] = "All"

    if "club_main" not in st.session_state:
        st.session_state["club_main"] = "All"

    if "free_only_filter" not in st.session_state:
        st.session_state["free_only_filter"] = False

    # Reset button
    if st.button("Reset filters", key="reset_filters"):
        st.session_state["competition_main"] = "All"
        st.session_state["platform_main"] = "All"
        st.session_state["club_main"] = "All"
        st.session_state["free_only_filter"] = False
        st.session_state["view_mode_state"] = "single"
        st.session_state["selected_date_state"] = unique_dates[0]
        st.session_state["range_start_state"] = unique_dates[0]
        st.session_state["range_end_state"] = unique_dates[0]
        st.rerun()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        selected_date = st.date_input(
            "Date",
            value=st.session_state["selected_date_state"],
            min_value=min(unique_dates),
            max_value=max(unique_dates),
            key="date_input_main",
        )

        # Only switch to single mode if user manually changes the date picker
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

    quick1, quick2, quick3, quick4 = st.columns(4)

    with quick1:
        if st.button("Today", key="quick_today"):
            today_date = pd.Timestamp.today().date()
            st.session_state["view_mode_state"] = "single"
            st.session_state["selected_date_state"] = get_next_available_date(
                today_date, unique_dates
            )
            st.rerun()

    with quick2:
        if st.button("Tomorrow", key="quick_tomorrow"):
            tomorrow_date = (pd.Timestamp.today() + pd.Timedelta(days=1)).date()
            st.session_state["view_mode_state"] = "single"
            st.session_state["selected_date_state"] = get_next_available_date(
                tomorrow_date, unique_dates
            )
            st.rerun()

    with quick3:
        if st.button("Next 7 days", key="quick_next_7_days"):
            today_date = pd.Timestamp.today().date()
            end_date = today_date + pd.Timedelta(days=6)
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = today_date
            st.session_state["range_end_state"] = end_date
            st.rerun()

    with quick4:
        if st.button("Next weekend", key="quick_next_weekend"):
            today_date = pd.Timestamp.today().date()
            days_until_next_saturday = ((5 - today_date.weekday()) % 7) or 7
            next_saturday = today_date + pd.Timedelta(days=days_until_next_saturday)
            next_sunday = next_saturday + pd.Timedelta(days=1)
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = next_saturday
            st.session_state["range_end_state"] = next_sunday
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
    else:
        pretty_start = format_pretty_date(range_start)
        pretty_end = format_pretty_date(range_end)
        st.info(f"Showing fixtures from {pretty_start} to {pretty_end}.")

    today = pd.Timestamp.today().date()
    if view_mode == "single" and selected_date == today:
        st.success("Today's matches ⚽")

    st.divider()

    if filtered.empty:
        st.warning("No matches found for those filters.")
    else:
        if view_mode == "single":
            st.write(f"### {len(filtered)} match(es) on {pretty_date}")
        else:
            st.write(f"### {len(filtered)} match(es) in this date range")

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