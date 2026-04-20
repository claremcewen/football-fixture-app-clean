from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import os
import subprocess

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
    weekday = today_date.weekday()

    if weekday < 5:
        start = today_date + timedelta(days=(5 - weekday))
        end = start + timedelta(days=1)
    elif weekday == 5:
        start = today_date
        end = today_date + timedelta(days=1)
    else:
        start = today_date
        end = today_date

    return start, end


def get_last_updated_text():
    if not DATA_FILE.exists():
        return "No fixture file yet"
    dt = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
    return dt.strftime("%A %d %B %Y, %H:%M")


@st.cache_data(ttl="30m")
def load_data():
    if not DATA_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(DATA_FILE)

    if df.empty:
        return df

    for col in ["venue", "watch_platforms", "watch_notes", "official_source"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).replace("nan", "")

    df["kickoff"] = pd.to_datetime(df["kickoff_uk"], errors="coerce")
    df = df.dropna(subset=["kickoff"]).copy()

    df = df.drop_duplicates(subset=["home_team", "away_team", "kickoff_uk"])

    df["date"] = df["kickoff"].dt.date
    df["competition_group"] = df["competition"].apply(simplify_competition_label)

    return df.sort_values("kickoff").reset_index(drop=True)


def filter_data(df, competition, platform, club, free_only, view_mode,
                selected_date=None, start_date=None, end_date=None):

    filtered = df.copy()

    if view_mode == "single":
        filtered = filtered[filtered["date"] == selected_date]

    elif view_mode == "range":
        filtered = filtered[
            (filtered["date"] >= start_date) &
            (filtered["date"] <= end_date)
        ]

    if competition != "All":
        filtered = filtered[filtered["competition_group"] == competition]

    if platform != "All":
        filtered = filtered[
            filtered["watch_platforms"].str.contains(platform, case=False, na=False)
        ]

    if club != "All":
        filtered = filtered[
            (filtered["home_team"] == club) |
            (filtered["away_team"] == club)
        ]

    if free_only:
        filtered = filtered[
            filtered["watch_platforms"].str.contains(
                "BBC|YouTube|ITV", case=False, na=False
            )
        ]

    return filtered.sort_values("kickoff")


def match_card(row):
    with st.container():
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader(f"{row['home_team']} vs {row['away_team']}")
            st.caption(row["competition"])

            kickoff = row["kickoff"]
            st.write(
                f"{kickoff.strftime('%A')} {kickoff.day} "
                f"{kickoff.strftime('%B')}, {kickoff.strftime('%H:%M')}"
            )

            st.write(f"Venue: {row.get('venue') or 'TBC'}")

        with col2:
            watch = str(row.get("watch_platforms", "")).strip()
            watch_lower = watch.lower()

            if any(x in watch_lower for x in ["bbc", "youtube", "itv"]):
                st.markdown("🟢 **Free to watch**")

            st.write(f"Watch: {watch if watch else 'TBC'}")

        st.divider()


def format_date(d):
    ts = pd.Timestamp(d)
    return f"{ts.strftime('%A')} {ts.day} {ts.strftime('%B %Y')}"


def main():
    df = load_data()

    # HEADER
    left, right = st.columns([3, 1])

    with left:
        st.title("⚽ Women's Football Watch Guide")
        st.markdown("Find upcoming women's football matches and where to watch them.")
        st.caption(f"Last updated: {get_last_updated_text()}")

    with right:
        if st.button("🔄 Update"):
            with st.spinner("Updating..."):
                subprocess.run(
                    ["python", str(APP_DIR / "scripts" / "update_fixtures.py")]
                )
            load_data.clear()
            st.rerun()

    if df.empty:
        st.warning("No fixture data found.")
        return

    today = pd.Timestamp.today().date()

    # DEFAULT VIEW = NEXT 7 DAYS
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "range"
        st.session_state.start = today
        st.session_state.end = today + timedelta(days=6)

    # METRICS
    m1, m2 = st.columns(2)

    with m1:
        st.metric("Matches loaded", len(df))

    with m2:
        st.metric("Competitions", df["competition"].nunique())

    # NEXT FIXTURE (smaller)
    next_match = df[df["kickoff"] >= pd.Timestamp.now()]
    if not next_match.empty:
        nm = next_match.iloc[0]
        st.markdown(
            f"**Next fixture:** {nm['home_team']} vs {nm['away_team']}"
        )

    st.divider()

    # FILTERS
    competitions = ["All"] + sorted(df["competition_group"].unique())
    clubs = ["All"] + sorted(
        pd.unique(pd.concat([df["home_team"], df["away_team"]]))
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        competition = st.selectbox("Competition", competitions)

    with c2:
        club = st.selectbox("Club", clubs)

    with c3:
        free_only = st.checkbox("Free to watch only")

    # RESET BUTTON (now correctly placed)
    if st.button("Reset filters"):
        st.rerun()

    st.divider()

    # QUICK BUTTONS
    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("Today"):
            st.session_state.view_mode = "single"
            st.session_state.selected = today

    with b2:
        if st.button("Weekend"):
            s, e = get_weekend_range(today)
            st.session_state.view_mode = "range"
            st.session_state.start = s
            st.session_state.end = e

    with b3:
        if st.button("Next 7 Days"):
            st.session_state.view_mode = "range"
            st.session_state.start = today
            st.session_state.end = today + timedelta(days=6)

    with b4:
        if st.button("Full List"):
            st.session_state.view_mode = "all"

    # FILTER DATA
    view = st.session_state.view_mode

    if view == "single":
        filtered = filter_data(df, competition, "", club, free_only,
                               "single", selected_date=st.session_state.selected)
    elif view == "range":
        filtered = filter_data(df, competition, "", club, free_only,
                               "range", start_date=st.session_state.start,
                               end_date=st.session_state.end)
    else:
        filtered = df

    # DISPLAY
    if filtered.empty:
        st.warning("No fixtures match your filters.")
    else:
        current = None
        for _, row in filtered.iterrows():
            if row["date"] != current:
                st.markdown(f"### 📅 {format_date(row['date'])}")
                current = row["date"]

            match_card(row)


if __name__ == "__main__":
    main()