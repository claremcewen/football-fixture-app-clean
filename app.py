from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "data" / "fixtures_all.csv"
LOGO_FILE = APP_DIR / "assets" / "logo.png"

st.set_page_config(
    page_title="She Can Kick It",
    page_icon=str(LOGO_FILE) if LOGO_FILE.exists() else "⚽",
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
    "England Women U20": "all",
    "UWCL": "all",
    "WSL": "next_round",
    "WSL2": "next_round",
    "NWSL": "next_round",
    "Northern Premier Division": "next_round",
    "Southern Premier Division": "next_round",
    "Division 1 North": "next_round",
    "Division 1 Midlands": "next_round",
    "Division 1 South East": "next_round",
    "Division 1 South West": "next_round",
    "FAWNL Cup": "next_round",
    "SWPL 1": "next_round",
    "Subway Players Cup": "next_round",
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
# a broad (not narrowed-to-one-competition) scope pulls teams from every
# competition at once.
NATIONAL_TEAM_COMPETITIONS: set[str] = {"England Women", "England Women U20"}

# Small color-coded dot per competition on each match card, purely for
# visual grouping - an original palette, not official league/team colors
# or logos, to stay clear of any branding/trademark concerns.
COMPETITION_COLOR: dict[str, str] = {
    "WSL": "#0F6E56",
    "WSL2": "#185FA5",
    "England Women": "#2E8B57",
    "England Women U20": "#3E9E8C",
    "UWCL": "#2C7DA0",
    "NWSL": "#1B998B",
    "Northern Premier Division": "#3B6D11",
    "Southern Premier Division": "#3A6B8A",
    "Division 1 North": "#2E6F40",
    "Division 1 Midlands": "#0B5563",
    "Division 1 South East": "#085041",
    "Division 1 South West": "#265C7A",
    "FAWNL Cup": "#4C9A2A",
    "SWPL 1": "#1D6E9E",
    "Subway Players Cup": "#4A8B3B",
}
DEFAULT_COMPETITION_COLOR = "#5F5E5A"

# Competition picker is a small hierarchy, not one flat list - FAWNL_GROUP
# and INTERNATIONALS_GROUP are containers that reveal a second (FAWNL: a
# third) picker instead of being directly selectable. Every other entry
# here is a real competition_group value, selectable immediately.
FAWNL_GROUP = "FAWNL"
INTERNATIONALS_GROUP = "Internationals"

TOP_LEVEL_COMPETITIONS = [
    "WSL",
    "WSL2",
    FAWNL_GROUP,
    "FAWNL Cup",
    "Subway Players Cup",
    "SWPL 1",
    "NWSL",
    "UWCL",
    INTERNATIONALS_GROUP,
]

# FAWNL: tier picked first, then a division within that tier (or "All of
# Tier N" to see the whole tier combined - previously parked as a future
# enhancement, now a natural fit for this picker).
FAWNL_TIERS: dict[str, list[str]] = {
    "Tier 3": ["Northern Premier Division", "Southern Premier Division"],
    "Tier 4": [
        "Division 1 North",
        "Division 1 Midlands",
        "Division 1 South East",
        "Division 1 South West",
    ],
}
ALL_OF_TIER_PREFIX = "All of "

# Internationals: flat list of national-team competitions - extend this as
# more get added (Scotland/Wales/Ireland etc are on the wishlist).
INTERNATIONAL_COMPETITIONS: list[str] = ["England Women", "England Women U20"]

# She Can Kick It brand identity.
BRAND_GREEN = "#7ED957"
BRAND_DARK_BLUE = "#145B8E"
BRAND_MID_BLUE = "#0597B2"
BRAND_CREAM = "#FAF2E9"
BRAND_SITE_URL = "https://shecankickit.com"
BRAND_SITE_LABEL = "shecankickit.com"
SUBSTACK_EMBED_URL = "https://theaccidentalcoach.substack.com/embed"

APP_CSS = f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {{
    font-family: 'Montserrat', sans-serif;
}}
/* Streamlit's default top padding leaves a lot of dead space above the
   fold on a phone before any fixtures are visible - trimmed down, but kept
   just past the fixed header toolbar's own height (60px) so content isn't
   rendered underneath it. */
.block-container {{
    padding-top: 4.5rem !important;
}}
h1, h2, h3, .wfg-brand-title {{
    font-family: 'Anton', sans-serif;
    letter-spacing: 0.02em;
}}
.wfg-brand-title {{
    font-size: 32px;
    color: {BRAND_DARK_BLUE};
    margin: 0 0 2px;
    line-height: 1.1;
}}
.wfg-status {{
    border: none;
    background: {BRAND_GREEN};
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 500;
    color: #0B3D0B;
    margin-bottom: 0.5rem;
    display: inline-block;
}}
.st-key-header_band {{
    background: {BRAND_DARK_BLUE};
    border-radius: 12px;
    padding: 1rem 1rem 0.5rem;
    margin-bottom: 1rem;
}}
.st-key-header_band [data-testid="stCaptionContainer"] {{
    color: {BRAND_CREAM} !important;
}}
.wfg-section-heading {{
    font-family: 'Anton', sans-serif;
    font-size: 15px;
    color: {BRAND_DARK_BLUE};
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 1.25rem 0 0.5rem;
}}
.wfg-date-heading {{
    font-family: 'Anton', sans-serif;
    font-size: 17px;
    color: {BRAND_DARK_BLUE};
    margin: 1.25rem 0 0.5rem;
}}
.wfg-card {{
    border: 1px solid {BRAND_MID_BLUE}40;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 10px;
    background: #FFFFFF;
}}
.wfg-card-top {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}}
.wfg-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
}}
.wfg-competition {{
    font-size: 11px;
    font-weight: 600;
    color: {BRAND_MID_BLUE};
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}
.wfg-card-body {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
}}
.wfg-teams {{
    font-size: 15px;
    font-weight: 700;
    margin: 0;
    color: {BRAND_DARK_BLUE};
}}
.wfg-meta {{
    font-size: 12px;
    color: #5F5E5A;
    margin: 2px 0 0;
}}
.wfg-venue {{
    font-size: 12px;
    color: #5F5E5A;
    margin: 0;
    white-space: nowrap;
    text-align: right;
}}
.wfg-footer {{
    text-align: center;
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid {BRAND_MID_BLUE}30;
}}
.wfg-footer a {{
    font-size: 13px;
    font-weight: 600;
    color: {BRAND_MID_BLUE};
    text-decoration: none;
}}
.st-key-locked_gate {{
    border: 1px solid {BRAND_MID_BLUE}40;
    border-radius: 12px;
    padding: 1.25rem 1.1rem;
    margin: 1rem 0;
    background: #FFFFFF;
    text-align: center;
}}
.st-key-locked_gate iframe {{
    border-radius: 8px;
}}
.wfg-subscribe-heading {{
    font-family: 'Anton', sans-serif;
    font-size: 17px;
    color: {BRAND_DARK_BLUE};
    margin: 0 0 4px;
}}
.wfg-subscribe-body {{
    font-size: 13px;
    color: #5F5E5A;
    margin: 0 0 12px;
}}
/* Keep specific rows side by side even on narrow (mobile) screens, where
   Streamlit's default column behaviour forces every column to nearly full
   width - stacking each one on its own line. Scoped with :has() to just
   the rows that need it (logo+caption, the three quick-date buttons);
   Competition/Club/Free-to-air etc still stack normally, since those need
   the full width to stay usable on a small screen. */
div[data-testid="stHorizontalBlock"]:has(.st-key-header_logo),
div[data-testid="stHorizontalBlock"]:has(.st-key-quick_today) {{
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 8px !important;
}}

/* Header: logo column stays a fixed, content-sized width; the caption
   column grows to fill whatever's left. Without this split, both columns
   grow equally (see below) and the logo ends up floating in a much wider
   box than its image on a large screen. */
div[data-testid="stHorizontalBlock"]:has(.st-key-header_logo) > div[data-testid="stColumn"] {{
    min-width: 0 !important;
    width: auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(.st-key-header_logo) > div[data-testid="stColumn"]:first-child {{
    flex: 0 0 auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(.st-key-header_logo) > div[data-testid="stColumn"]:last-child {{
    flex: 1 1 auto !important;
}}

/* Quick-date buttons: sized to their own content, not stretched to fill
   the row - "flex: 1 1 0" (equal grow) looked fine on a narrow phone
   (little space to grow into) but spread the buttons out with large gaps
   on a wide laptop screen, since each column grew to a full third of a
   much wider row. */
div[data-testid="stHorizontalBlock"]:has(.st-key-quick_today) {{
    justify-content: flex-start !important;
}}
div[data-testid="stHorizontalBlock"]:has(.st-key-quick_today) > div[data-testid="stColumn"] {{
    min-width: 0 !important;
    width: auto !important;
    flex: 0 0 auto !important;
}}
div[data-testid="stHorizontalBlock"]:has(.st-key-quick_today) button {{
    padding: 0.4rem 0.55rem !important;
    font-size: 12px !important;
    white-space: nowrap;
    border-radius: 20px !important;
}}
/* Today/This weekend/Next 7 Days are the primary navigation actions -
   filled pills, alternating green/dark blue so they read as distinct
   actions rather than one undifferentiated block. Reset is a
   lower-emphasis clearing action, styled as an outline pill instead so
   it doesn't compete visually. */
.st-key-quick_today button,
.st-key-quick_next_7_days button {{
    background: {BRAND_GREEN} !important;
    color: #0B3D0B !important;
    border: none !important;
}}
.st-key-quick_today button:hover,
.st-key-quick_next_7_days button:hover {{
    background: {BRAND_GREEN}CC !important;
    color: #0B3D0B !important;
}}
.st-key-quick_weekend button {{
    background: {BRAND_DARK_BLUE} !important;
    color: {BRAND_CREAM} !important;
    border: none !important;
}}
.st-key-quick_weekend button:hover {{
    background: {BRAND_DARK_BLUE}CC !important;
    color: {BRAND_CREAM} !important;
}}
.st-key-reset_filters button {{
    background: transparent !important;
    color: {BRAND_DARK_BLUE} !important;
    border: 1px solid {BRAND_DARK_BLUE} !important;
}}
.st-key-reset_filters button:hover {{
    background: {BRAND_DARK_BLUE}14 !important;
    color: {BRAND_DARK_BLUE} !important;
}}
</style>
"""


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
                "tier",
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
    competition: str | list[str],
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
        # A list means an "All of Tier N" aggregate scope (several
        # competition_group values at once) rather than a single one.
        groups = competition if isinstance(competition, list) else [competition]
        filtered = filtered[filtered["competition_group"].isin(groups)]

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
                "BBC|YouTube|ITV|BBC iPlayer|BBC Sport Website|Channel 4|All4|All 4",
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
    color = COMPETITION_COLOR.get(row.get("competition_group"), DEFAULT_COMPETITION_COLOR)

    kickoff = row["kickoff"]
    pretty_kickoff = f"{kickoff.strftime('%a')} {kickoff.day} {kickoff.strftime('%b')} · {kickoff.strftime('%H:%M')}"

    watch_platforms = row.get("watch_platforms", "")
    watch_text = (
        str(watch_platforms)
        if pd.notna(watch_platforms) and str(watch_platforms).strip()
        else "TBC"
    )
    venue = row.get("venue", "-")
    venue = str(venue) if pd.notna(venue) and str(venue).strip() else "-"

    meta_parts = [pretty_kickoff, watch_text]
    notes = row.get("watch_notes", "")
    if pd.notna(notes) and str(notes).strip():
        meta_parts.append(str(notes))

    st.markdown(
        f"""
        <div class="wfg-card">
            <div class="wfg-card-top">
                <span class="wfg-dot" style="background: {html.escape(color)};"></span>
                <span class="wfg-competition">{html.escape(str(row['competition']))}</span>
            </div>
            <div class="wfg-card-body">
                <div>
                    <p class="wfg-teams">{html.escape(str(row['home_team']))} vs {html.escape(str(row['away_team']))}</p>
                    <p class="wfg-meta">{html.escape(" · ".join(meta_parts))}</p>
                </div>
                <p class="wfg-venue">{html.escape(str(venue))}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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


def render_status(text: str) -> None:
    st.markdown(f'<div class="wfg-status">{html.escape(text)}</div>', unsafe_allow_html=True)


def render_date_heading(text: str) -> None:
    st.markdown(f'<p class="wfg-date-heading">{html.escape(text)}</p>', unsafe_allow_html=True)


def render_section_heading(text: str) -> None:
    st.markdown(f'<p class="wfg-section-heading">{html.escape(text)}</p>', unsafe_allow_html=True)


def resolve_competition_selection() -> tuple:
    """Reads the (possibly multi-level) Competition picker's current
    session-state values and returns (filter_value, display_label):
    - filter_value: what to filter fixtures by - the ALL_THIS_WEEK/
      ALL_FULL_LIST sentinel, a single competition_group string, or a
      list of competition_group strings (the "All of Tier N" case).
    - display_label: a short human-readable label for the status line
      and Club dropdown ("WSL", "FAWNL - Tier 3", "England Women", "all").
    Session-state keys for levels below the current top-level pick may
    not exist yet on a fresh session - .get() with the same defaults
    used at init time keeps this safe to call before that init block runs.
    """
    top = st.session_state.get("competition_top_main", ALL_THIS_WEEK)

    if top in (ALL_THIS_WEEK, ALL_FULL_LIST):
        return top, "all"

    if top == FAWNL_GROUP:
        tier = st.session_state.get("competition_tier_main", "Tier 3")
        all_of_tier_label = f"{ALL_OF_TIER_PREFIX}{tier}"
        division = st.session_state.get("competition_division_main", all_of_tier_label)
        if division == all_of_tier_label:
            return FAWNL_TIERS[tier], f"FAWNL - {tier}"
        return division, f"FAWNL - {division}"

    if top == INTERNATIONALS_GROUP:
        team = st.session_state.get("competition_intl_main", INTERNATIONAL_COMPETITIONS[0])
        return team, team

    return top, top


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
    happened this past Friday shouldn't reappear). Once the weekend itself
    is over (i.e. today is Monday), this points to the *next* weekend
    rather than lingering on the one that just finished."""
    weekday = today.weekday()  # Mon=0 ... Sun=6

    if weekday in (4, 5, 6):  # Fri/Sat/Sun - this weekend has already started
        friday = today - pd.Timedelta(days=(weekday - 4))
    else:  # Mon/Tue/Wed/Thu - the upcoming Friday
        friday = today + pd.Timedelta(days=((4 - weekday) % 7))

    monday = friday + pd.Timedelta(days=3)
    return max(friday, today), monday


def apply_competition_change() -> None:
    """Reset the date view (and the now-stale club filter) whenever any
    level of the Competition picker changes, since a fixed 'next 7 days'
    makes sense for a weekly league but would often show nothing for a
    sparse international one, and the Club list is scoped per competition.
    Runs as the on_change callback for every level (top/tier/division/
    team), so it always sees the just-updated session-state values."""
    st.session_state["club_main"] = "All"
    today = pd.Timestamp.today().date()

    top = st.session_state["competition_top_main"]

    if top == ALL_THIS_WEEK:
        st.session_state["view_mode_state"] = "range"
        st.session_state["range_start_state"] = today
        st.session_state["range_end_state"] = today + pd.Timedelta(days=6)
        return

    if top == ALL_FULL_LIST:
        st.session_state["view_mode_state"] = "all"
        return

    filter_value, _ = resolve_competition_selection()

    if isinstance(filter_value, list):
        # An "All of Tier N" aggregate spans several divisions at once -
        # too sparse/uneven across them for "next round" clustering to
        # mean much, so just show everything upcoming instead.
        st.session_state["view_mode_state"] = "all"
        return

    mode = COMPETITION_DEFAULT_VIEW.get(filter_value, DEFAULT_VIEW_FALLBACK)

    if mode == "all":
        st.session_state["view_mode_state"] = "all"
        return

    start, end = next_round_window(load_data(), filter_value, today)
    st.session_state["view_mode_state"] = "range"
    st.session_state["range_start_state"] = start
    st.session_state["range_end_state"] = end


def apply_tier_change() -> None:
    """The FAWNL division picker's valid options depend on which tier is
    selected - reset it to that tier's "All of Tier N" default first (a
    stale division from a previously-selected tier would otherwise not be
    a valid option and Streamlit would raise), then apply the same
    date-view reset as any other Competition change."""
    tier = st.session_state["competition_tier_main"]
    st.session_state["competition_division_main"] = f"{ALL_OF_TIER_PREFIX}{tier}"
    apply_competition_change()


def apply_date_lookup() -> None:
    """Fires only on a genuine user pick in the 'look up a specific date'
    widget (Streamlit's on_change), not on the widget's own first-render
    clamping - a plain value comparison would wrongly treat that clamp as
    a user edit whenever today falls outside the loaded data's range."""
    st.session_state["view_mode_state"] = "single"
    st.session_state["selected_date_state"] = st.session_state["date_input_main"]


def get_access_code() -> str | None:
    return st.secrets.get("ACCESS_CODE")


def is_unlocked() -> bool:
    """Free-to-use, gated behind a Substack subscription rather than open
    to anyone - a code shared with subscribers (via the Substack welcome
    email) unlocks it, either by following a link with ?access=CODE or by
    typing the code in directly. Not meant to be airtight (a code can be
    shared) - just enough friction that "subscribe first" is the intended
    path, per the user's explicit ask."""
    if st.session_state.get("_unlocked"):
        return True

    access_code = get_access_code()
    if not access_code:
        # No code configured (e.g. local dev without a secrets.toml) -
        # don't lock everyone out over a missing config, just skip the gate.
        return True

    if st.query_params.get("access") == access_code:
        st.session_state["_unlocked"] = True
        return True

    return False


def render_locked_screen() -> None:
    with st.container(key="locked_gate"):
        st.html(
            """
            <p class="wfg-subscribe-heading">This tracker is free for subscribers</p>
            <p class="wfg-subscribe-body">Subscribe to "She Can Kick It" below to get your
            access code by email, sent straight away.</p>
            """
        )
        components.iframe(SUBSTACK_EMBED_URL, height=150, scrolling=False)

        st.html('<p class="wfg-subscribe-body">Already got a code?</p>')
        code_input = st.text_input(
            "Access code", key="access_code_input", label_visibility="collapsed"
        )
        if st.button("Unlock", key="unlock_button"):
            entered = code_input.strip()
            if entered and entered == get_access_code():
                # Baking the code into the URL (not just session_state) means
                # this link keeps working on future visits without typing
                # the code again - same as clicking a link that already has
                # it, per the user's "one-time only" requirement.
                st.session_state["_unlocked"] = True
                st.query_params["access"] = entered
                st.rerun()
            else:
                st.error(
                    "That code doesn't look right - subscribe above to get one."
                )


def main():
    # st.html (not st.markdown) - st.markdown runs content through Streamlit's
    # markdown-to-HTML converter even with unsafe_allow_html=True, which was
    # silently mangling/truncating this long CSS block partway through.
    # st.html() injects raw HTML/CSS with no markdown pre-processing.
    st.html(APP_CSS)

    # Logo and caption side by side on a dark blue band (".st-key-header_band"
    # in APP_CSS) - kept in one row even on a narrow phone screen via the
    # ".st-key-header_logo" CSS rule, rather than letting Streamlit stack
    # them (which used to push the caption, and everything below it,
    # further down the page on mobile).
    with st.container(key="header_band"):
        header_logo_col, header_text_col = st.columns([1, 4])

        with header_logo_col:
            with st.container(key="header_logo"):
                if LOGO_FILE.exists():
                    st.image(str(LOGO_FILE), width=70)
                else:
                    st.markdown(
                        '<p class="wfg-brand-title">She Can Kick It</p>',
                        unsafe_allow_html=True,
                    )

        with header_text_col:
            st.caption("Women's football fixtures - and where to watch them.")

    if not is_unlocked():
        render_locked_screen()
        st.stop()

    df = load_data()

    if df.empty:
        st.warning(
            "No fixture data found yet. The fixture CSV has not been generated yet."
        )
        return

    today_date = pd.Timestamp.today().date()

    unique_dates = sorted(df["date"].unique())

    known_competitions = set(df["competition_group"].dropna().unique().tolist())

    def top_level_has_data(item: str) -> bool:
        if item == FAWNL_GROUP:
            return any(d in known_competitions for divs in FAWNL_TIERS.values() for d in divs)
        if item == INTERNATIONALS_GROUP:
            return any(c in known_competitions for c in INTERNATIONAL_COMPETITIONS)
        return item in known_competitions

    present_top_level = [item for item in TOP_LEVEL_COMPETITIONS if top_level_has_data(item)]
    competition_top_options = [ALL_THIS_WEEK] + present_top_level + [ALL_FULL_LIST]
    present_international_competitions = [
        c for c in INTERNATIONAL_COMPETITIONS if c in known_competitions
    ]

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
    if "competition_top_main" not in st.session_state:
        st.session_state["competition_top_main"] = ALL_THIS_WEEK
    if "competition_tier_main" not in st.session_state:
        st.session_state["competition_tier_main"] = "Tier 3"
    if "competition_division_main" not in st.session_state:
        st.session_state["competition_division_main"] = f"{ALL_OF_TIER_PREFIX}Tier 3"
    if "competition_intl_main" not in st.session_state and INTERNATIONAL_COMPETITIONS:
        st.session_state["competition_intl_main"] = INTERNATIONAL_COMPETITIONS[0]
    if "platform_main" not in st.session_state:
        st.session_state["platform_main"] = "All"
    if "club_main" not in st.session_state:
        st.session_state["club_main"] = "All"
    if "free_only_filter" not in st.session_state:
        st.session_state["free_only_filter"] = False

    # Reset is applied here, before any widget below is instantiated -
    # Streamlit forbids writing to a widget's session_state key once that
    # widget has already been created in the same script run, so the actual
    # button click just sets this flag and reruns; the write happens on the
    # next run, before Competition/Club/Free-to-air/Watch platform exist yet.
    # Filters only - deliberately does NOT touch view_mode_state/date state,
    # so clearing filters doesn't also throw away whatever date/view (e.g.
    # "This weekend") you were looking at.
    if st.session_state.pop("_pending_reset", False):
        st.session_state["competition_top_main"] = ALL_THIS_WEEK
        st.session_state["platform_main"] = "All"
        st.session_state["club_main"] = "All"
        st.session_state["free_only_filter"] = False

    # Read current state up front so the status banner can sit above the
    # controls that drive it (Streamlit reruns top-to-bottom on every
    # interaction, so this reflects whatever was last selected/clicked).
    # resolve_competition_selection() reads session-state directly, so this
    # is safe to call before the Competition picker's own widgets render
    # further down - it reflects whatever the user last picked, same as
    # reading a plain session-state key did before this was a hierarchy.
    filter_value, comp_label = resolve_competition_selection()
    view_mode = st.session_state["view_mode_state"]
    selected_date = st.session_state["selected_date_state"]
    range_start = st.session_state["range_start_state"]
    range_end = st.session_state["range_end_state"]

    status_col, action_col = st.columns([3, 1])

    with status_col:
        if view_mode == "single":
            pretty_date = format_pretty_date(selected_date)
            render_status(f"Showing {comp_label} fixtures for {pretty_date}.")
        elif view_mode == "range":
            pretty_start = format_pretty_date(range_start)
            pretty_end = format_pretty_date(range_end)
            render_status(f"Showing {comp_label} fixtures from {pretty_start} to {pretty_end}.")
        else:
            if comp_label == "all":
                render_status("Showing all upcoming fixtures.")
            else:
                render_status(f"Showing all upcoming {comp_label} fixtures.")

    with action_col:
        # Hidden once already showing "all", and for the unscoped
        # ALL_THIS_WEEK competition view - ALL_FULL_LIST in the dropdown
        # covers that case directly, so this button would otherwise
        # duplicate it.
        if view_mode != "all" and filter_value != ALL_THIS_WEEK:
            if st.button("Show all upcoming", key="show_all_upcoming"):
                st.session_state["view_mode_state"] = "all"
                st.rerun()

    # All kickoff times are UK local time (BST/GMT) - worth stating plainly
    # since some sources publish times in a different host country's own
    # local time before conversion (e.g. WAFCON's Morocco kickoff times,
    # when that competition is active again).
    st.caption("All times shown in UK time (BST/GMT).")

    # Quick actions - Today/This weekend/Next 7 Days/Reset are kept in their
    # own row (see the ".st-key-quick_today" CSS rule in APP_CSS) so they
    # stay side by side even on a narrow phone screen, where Streamlit's
    # default column behaviour would otherwise stack each one on its own
    # line. Placed right after the status line, before the fixture list,
    # so they're reachable without opening the Filters expander below.
    a1, a2, a3, a4 = st.columns(4)

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

    with a3:
        if st.button("Next 7 Days", key="quick_next_7_days"):
            st.session_state["view_mode_state"] = "range"
            st.session_state["range_start_state"] = today_date
            st.session_state["range_end_state"] = today_date + pd.Timedelta(days=6)
            st.rerun()

    with a4:
        if st.button("Reset", key="reset_filters"):
            st.session_state["_pending_reset"] = True
            st.rerun()

    # Filters collapsed by default - Competition/Club/Free-to-air/Watch
    # platform/date lookup all live here so fixtures are visible right away
    # on a phone without scrolling past a wall of controls first; still one
    # tap away when actually needed.
    with st.expander("Filters"):
        # Competition is a small hierarchy, not one flat list - FAWNL and
        # Internationals reveal a second (FAWNL: a third) picker once
        # chosen; everything else is selectable directly, no extra step.
        top = st.selectbox(
            "Competition",
            competition_top_options,
            key="competition_top_main",
            on_change=apply_competition_change,
        )

        if top == FAWNL_GROUP:
            tier_col, division_col = st.columns(2)

            with tier_col:
                tier = st.selectbox(
                    "Tier",
                    list(FAWNL_TIERS.keys()),
                    key="competition_tier_main",
                    on_change=apply_tier_change,
                )

            # "All of Tier N" (see FAWNL_TIERS) sits alongside the specific
            # divisions as a valid stopping point, not just a fallback.
            division_options = [f"{ALL_OF_TIER_PREFIX}{tier}"] + FAWNL_TIERS[tier]
            if st.session_state["competition_division_main"] not in division_options:
                st.session_state["competition_division_main"] = division_options[0]

            with division_col:
                st.selectbox(
                    "Division",
                    division_options,
                    key="competition_division_main",
                    on_change=apply_competition_change,
                )
        elif top == INTERNATIONALS_GROUP:
            # Guards against a stale pick from a team whose fixtures have
            # since dropped out of the data entirely (e.g. an off-season
            # senior team with no youth fixtures scheduled either way).
            if st.session_state["competition_intl_main"] not in present_international_competitions:
                st.session_state["competition_intl_main"] = present_international_competitions[0]

            st.selectbox(
                "Team",
                present_international_competitions,
                key="competition_intl_main",
                on_change=apply_competition_change,
            )

        # filter_value/comp_label were already resolved above (for the
        # status line) from the same session-state these widgets just
        # displayed/confirmed - safe to reuse rather than re-resolving.
        is_national_team_competition = (
            isinstance(filter_value, str) and filter_value in NATIONAL_TEAM_COMPETITIONS
        )

        if is_national_team_competition:
            competition_scope = df.iloc[0:0]
        elif filter_value in (ALL_THIS_WEEK, ALL_FULL_LIST):
            # Every club at once, regardless of which competition (if any)
            # is narrowed - national teams excluded, since "England"/
            # "Greece" etc aren't a fixed set of clubs to filter by. Club
            # is never locked behind picking a competition first, so a
            # club can be searched for across every competition at once.
            competition_scope = df[~df["competition_group"].isin(NATIONAL_TEAM_COMPETITIONS)]
        elif isinstance(filter_value, list):
            competition_scope = df[df["competition_group"].isin(filter_value)]
        else:
            competition_scope = df[df["competition_group"] == filter_value]

        clubs = ["All"] + sorted(
            pd.unique(
                pd.concat([competition_scope["home_team"], competition_scope["away_team"]])
            ).tolist()
        )
        if st.session_state["club_main"] not in clubs:
            st.session_state["club_main"] = "All"

        club_col, free_col = st.columns(2)

        with club_col:
            if is_national_team_competition:
                club_label = "Club"
                club_help = "Not applicable for international fixtures."
            elif comp_label == "all":
                club_label = "Club (all leagues)"
                club_help = None
            else:
                club_label = f"Club ({comp_label})"
                club_help = None

            club = st.selectbox(
                club_label,
                clubs,
                key="club_main",
                disabled=is_national_team_competition,
                help=club_help,
            )

        with free_col:
            free_only = st.toggle(
                "Free-to-air only (UK)",
                key="free_only_filter",
                help="BBC, ITV, Channel 4 or YouTube",
            )

        st.markdown("**More filters**")
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
        filter_value,
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
            filter_value,
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
            render_section_heading("Fixtures in the next 7 days")

            current_group_date = None
            for _, row in next_7_days.iterrows():
                row_date = row["date"]

                if row_date != current_group_date:
                    render_date_heading(format_pretty_date(row_date))
                    current_group_date = row_date

                match_card(row)

            make_download(next_7_days)

    elif filtered.empty:
        st.warning("No matches found for those filters.")

    else:
        if view_mode == "single":
            pretty_date = format_pretty_date(selected_date)
            render_section_heading(f"{len(filtered)} match(es) on {pretty_date}")
        elif view_mode == "range":
            render_section_heading(f"{len(filtered)} match(es) in this date range")
        else:
            render_section_heading(f"{len(filtered)} match(es) in all upcoming fixtures")

        current_group_date = None
        for _, row in filtered.iterrows():
            row_date = row["date"]

            if row_date != current_group_date:
                render_date_heading(format_pretty_date(row_date))
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

    st.caption(f"Last updated: {get_last_updated_text()}")

    st.markdown(
        f'<div class="wfg-footer"><a href="{BRAND_SITE_URL}" target="_blank">'
        f"{BRAND_SITE_LABEL}</a></div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
