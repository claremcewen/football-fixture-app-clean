from __future__ import annotations

from datetime import datetime
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

# Default view applied when a competition is selected from the dropdown.
# "all" - show every upcoming fixture. Used for sparse/international
#         competitions where there's rarely more than a handful at once.
# "next_round" - auto-detect the next cluster of fixture dates (see
#         next_round_window below) rather than a fixed day count, since
#         leagues don't all play on the same weekdays every week.
COMPETITION_DEFAULT_VIEW: dict[str, str] = {
    "England Women": "all",
    "UWCL": "all",
    "WSL": "next_round",
    "WSL2": "next_round",
    "NWSL": "next_round",
}
DEFAULT_VIEW_FALLBACK = "next_round"

# Fixtures within this many days of each other count as the same round.
# Tuned against NWSL's actual schedule, which clusters into blocks like
# Thu/Sat/Sun/Mon separated by ~3+ day gaps between rounds.
ROUND_CLUSTER_GAP_DAYS = 2

# Used only if a "next_round" competition has no upcoming fixtures at all
# (nothing to cluster) - falls back to a plain N-day window.
EMPTY_ROUND_FALLBACK_DAYS = 10

# Orders same-day fixtures when leagues clash, so the most-followed league
# surfaces first within a given day rather than strict kickoff-time order.
# Lower sorts first; adjust freely - unlisted competitions rank last.
COMPETITION_PRIORITY: dict[str, int] = {
    "WSL": 1,
    "WSL2": 2,
    "England Women": 3,
    "UWCL": 4,
    "NWSL": 5,
}
DEFAULT_PRIORITY_FALLBACK = 99

# Two "no specific league" dropdown entries, both explicitly qualified so
# neither reads as the more complete option by default:
# - ALL_THIS_WEEK is the default landing choice - a 7-day rolling window.
# - ALL_FULL_LIST shows every fixture, every league, no date limit at all,
#   and sits at the bottom of the dropdown list.
ALL_THIS_WEEK = "All (this week)"
ALL_FULL_LIST = "All Fixtures"

# Competitions where "Club" doesn't make sense - a single national team
# playing a different opponent each fixture, not a fixed set of clubs.
# Excluded from Club filtering entirely, and from the Club list even when
# ALL_FULL_LIST pulls teams from every competition at once.
NATIONAL_TEAM_COMPETITIONS: set[str] = {"England Women"}


def get_last_updated_text() -> str:
    if DATA_FILE.exists():
        updated = datetime.fromtimestamp(DATA_FILE.stat().st_mtime)
        return updated.strftime("%Y-%m-%d %H:%M")
    return "Unknown"


@st.cache_data
def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame(
            columns=[
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

    if competition not in (ALL_THIS_WEEK, ALL_FULL_LIST):
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
                "BBC|YouTube|ITV|BBC iPlayer|BBC Sport Website",
                case=False,
                na=False,
            )
        ]

    filtered = filtered.copy()
    filtered["_priority"] = filtered["competition_group"].map(
        lambda c: COMPETITION_PRIORITY.get(c, DEFAULT_PRIORITY_FALLBACK)
    )
    return filtered.sort_values(["date", "_priority", "kickoff"]).drop(columns="_priority")


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
            st.write(f"**Venue:** {row.get('venue', '-') or '-'}")

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


def competition_display(competition: str) -> str:
    if competition in (ALL_THIS_WEEK, ALL_FULL_LIST):
        return "all"
    return competition


def next_round_window(df: pd.DataFrame, competition: str, today) -> tuple:
    """Find the next 'round' of fixtures for a competition by clustering
    consecutive fixture dates, breaking wherever a gap larger than
    ROUND_CLUSTER_GAP_DAYS appears. This adapts to each league's actual
    schedule instead of assuming fixed weekdays or a fixed day count."""
    comp_dates = sorted(
        df[(df["competition_group"] == competition) & (df["date"] >= today)][
            "date"
        ].unique()
    )

    if not comp_dates:
        return today, today + pd.Timedelta(days=EMPTY_ROUND_FALLBACK_DAYS)

    start = comp_dates[0]
    end = comp_dates[0]
    for d in comp_dates[1:]:
        gap = (d - end).days
        if gap > ROUND_CLUSTER_GAP_DAYS:
            break
        end = d

    return start, end


def this_weekend_range(today) -> tuple:
    """Return the (start, end) of the current/upcoming Fri-Mon block,
    clamped so it never starts before today (a match that already
    happened this past Friday shouldn't reappear)."""
    weekday = today.weekday()  # Mon=0 ... Sun=6

    if weekday == 0:  # Monday - tail end of the weekend that started last Friday
        friday = today - pd.Timedelta(days=3)
    elif weekday in (4, 5, 6):  # Fri/Sat/Sun - this weekend has already started
        friday = today - pd.Timedelta(days=(weekday - 4))
    else:  # Tue/Wed/Thu - upcoming Friday
        friday = today + pd.Timedelta(days=(4 - weekday))

    monday = friday + pd.Timedelta(days=3)
    return max(friday, today), monday


def apply_competition_default_view() -> None:
    """Reset the date view (and the now-stale club filter) whenever the
    Competition dropdown changes, since a fixed 'next 7 days' makes sense
    for a weekly league but would often show nothing for a sparse
    international one, and the Club list is scoped per competition."""
    competition = st.session_state["competition_main"]
    st.session_state["club_main"] = "All"
    today = pd.Timestamp.today().date()

    if competition == ALL_THIS_WEEK:
        st.session_state["view_mode_state"] = "range"
        st.session_state["range_start_state"] = today
        st.session_state["range_end_state"] = today + pd.Timedelta(days=6)
        return

    if competition == ALL_FULL_LIST:
        st.session_state["view_mode_state"] = "all"
        return

    mode = COMPETITION_DEFAULT_VIEW.get(competition, DEFAULT_VIEW_FALLBACK)

    if mode == "all":
        st.session_state["view_mode_state"] = "all"
        return

    start, end = next_round_window(load_data(), competition, today)
    st.session_state["view_mode_state"] = "range"
    st.session_state["range_start_state"] = start
    st.session_state["range_end_state"] = end


def apply_date_lookup() -> None:
    """Fires only on a genuine user pick in the 'look up a specific date'
    widget (Streamlit's on_change), not on the widget's own first-render
    clamping - a plain value comparison would wrongly treat that clamp as
    a user edit whenever today falls outside the loaded data's range."""
    st.session_state["view_mode_state"] = "single"
    st.session_state["selected_date_state"] = st.session_state["date_input_main"]


def main():
    df = load_data()

    st.title("⚽ Women's Football Watch Guide")
    st.caption("WSL, WSL2, England Women, UWCL and NWSL from generated combined data.")

    if df.empty:
        st.warning(
            "No fixture data found yet. The fixture CSV has not been generated yet."
        )
        return

    today_date = pd.Timestamp.today().date()

    unique_dates = sorted(df["date"].unique())
    competitions = (
        [ALL_THIS_WEEK]
        + sorted(df["competition_group"].dropna().unique().tolist())
        + [ALL_FULL_LIST]
    )
    platforms = ["All"] + sorted(
        {
            p.strip()
            for cell in df["watch_platforms"].dropna()
            for p in str(cell).split(",")
            if p.strip()
        }
    )

    if "selected_date_state" not in st.session_state:
        st.session_state["selected_date_state"] = today_date
    if "view_mode_state" not in st.session_state:
        st.session_state["view_mode_state"] = "single"
    if "range_start_state" not in st.session_state:
        st.session_state["range_start_state"] = today_date
    if "range_end_state" not in st.session_state:
        st.session_state["range_end_state"] = today_date + pd.Timedelta(days=6)
    if "competition_main" not in st.session_state:
        st.session_state["competition_main"] = ALL_THIS_WEEK
    if "platform_main" not in st.session_state:
        st.session_state["platform_main"] = "All"
    if "club_main" not in st.session_state:
        st.session_state["club_main"] = "All"
    if "free_only_filter" not in st.session_state:
        st.session_state["free_only_filter"] = False

    st.caption(f"Last updated: {get_last_updated_text()}")

    # Read current state up front so the status banner can sit above the
    # controls that drive it (Streamlit reruns top-to-bottom on every
    # interaction, so this reflects whatever was last selected/clicked).
    competition = st.session_state["competition_main"]
    view_mode = st.session_state["view_mode_state"]
    selected_date = st.session_state["selected_date_state"]
    range_start = st.session_state["range_start_state"]
    range_end = st.session_state["range_end_state"]
    comp_label = competition_display(competition)

    status_col, action_col = st.columns([3, 1])

    with status_col:
        if view_mode == "single":
            pretty_date = format_pretty_date(selected_date)
            st.info(f"Showing {comp_label} fixtures for {pretty_date}.")
        elif view_mode == "range":
            pretty_start = format_pretty_date(range_start)
            pretty_end = format_pretty_date(range_end)
            st.info(f"Showing {comp_label} fixtures from {pretty_start} to {pretty_end}.")
        else:
            if comp_label == "all":
                st.info("Showing all upcoming fixtures.")
            else:
                st.info(f"Showing all upcoming {comp_label} fixtures.")

    with action_col:
        # Hidden once already showing "all", and for the unscoped
        # ALL_THIS_WEEK competition view - ALL_FULL_LIST in the dropdown
        # covers that case directly, so this button would otherwise
        # duplicate it.
        if view_mode != "all" and competition != ALL_THIS_WEEK:
            if st.button("Show all upcoming", key="show_all_upcoming"):
                st.session_state["view_mode_state"] = "all"
                st.rerun()

    # Primary controls: competition drives its own sensible default view,
    # club is scoped to whichever competition is currently selected.
    c1, c2, c3 = st.columns([1.4, 1.4, 1])

    with c1:
        competition = st.selectbox(
            "Competition",
            competitions,
            key="competition_main",
            on_change=apply_competition_default_view,
        )

    is_national_team_competition = competition in NATIONAL_TEAM_COMPETITIONS
    club_disabled = competition == ALL_THIS_WEEK or is_national_team_competition

    if club_disabled:
        competition_scope = df.iloc[0:0]
    elif competition == ALL_FULL_LIST:
        # Every club competition at once - national teams excluded, since
        # "England"/"Greece" etc aren't a fixed set of clubs to filter by.
        competition_scope = df[~df["competition_group"].isin(NATIONAL_TEAM_COMPETITIONS)]
    else:
        competition_scope = df[df["competition_group"] == competition]

    clubs = ["All"] + sorted(
        pd.unique(
            pd.concat([competition_scope["home_team"], competition_scope["away_team"]])
        ).tolist()
    )
    if st.session_state["club_main"] not in clubs:
        st.session_state["club_main"] = "All"

    with c2:
        if is_national_team_competition:
            club_label = "Club"
            club_help = "Not applicable for international fixtures."
        elif competition == ALL_THIS_WEEK:
            club_label = "Club"
            club_help = "Pick a competition first to filter by club."
        elif competition == ALL_FULL_LIST:
            club_label = "Club (all leagues)"
            club_help = None
        else:
            club_label = f"Club ({competition})"
            club_help = None

        club = st.selectbox(
            club_label,
            clubs,
            key="club_main",
            disabled=club_disabled,
            help=club_help,
        )

    with c3:
        free_only = st.toggle(
            "Free-to-air only (UK)",
            key="free_only_filter",
            help="BBC, ITV or YouTube",
        )

    # Quick actions
    a1, a2, spacer, a4 = st.columns([1, 1, 3, 1])

    with a1:
        if st.button("Today", key="quick_today"):
            st.session_state["view_mode_state"] = "single"
            st.session_state["selected_date_state"] = today_date
            st.rerun()

    with a2:
        if st.button("This weekend", key="quick_weekend"):
            start, end = this_weekend_range(today_date)
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = start
            st.session_state["range_end_state"] = end
            st.rerun()

    with a4:
        if st.button("Reset", key="reset_filters"):
            st.session_state["competition_main"] = ALL_THIS_WEEK
            st.session_state["platform_main"] = "All"
            st.session_state["club_main"] = "All"
            st.session_state["free_only_filter"] = False
            st.session_state["view_mode_state"] = "single"
            st.session_state["selected_date_state"] = today_date
            st.session_state["range_start_state"] = today_date
            st.session_state["range_end_state"] = today_date + pd.Timedelta(days=6)
            st.rerun()

    with st.expander("More filters"):
        f1, f2 = st.columns(2)

        with f1:
            platform = st.selectbox("Watch platform", platforms, key="platform_main")

        with f2:
            min_date = min(unique_dates)
            max_date = max(unique_dates)
            default_lookup_date = min(max(today_date, min_date), max_date)

            st.date_input(
                "Look up a specific date",
                value=default_lookup_date,
                min_value=min_date,
                max_value=max_date,
                key="date_input_main",
                on_change=apply_date_lookup,
            )

    st.divider()

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

    if view_mode == "single" and selected_date == today_date and filtered.empty:
        st.warning("No games today")

        next_7_days = filter_data(
            df,
            competition,
            platform,
            club,
            free_only,
            view_mode="range",
            start_date=today_date,
            end_date=today_date + pd.Timedelta(days=6),
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
            pretty_date = format_pretty_date(selected_date)
            st.write(f"### {len(filtered)} match(es) on {pretty_date}")
        elif view_mode == "range":
            st.write(f"### {len(filtered)} match(es) in this date range")
        else:
            st.write(f"### {len(filtered)} match(es) in all upcoming fixtures")

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


if __name__ == "__main__":
    main()
