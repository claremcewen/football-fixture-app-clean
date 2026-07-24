from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from .common import build_df, fetch_html, to_uk_iso_from_tz

WAFCON_URL = "https://en.wikipedia.org/wiki/2026_Women%27s_Africa_Cup_of_Nations"
COMPETITION_LABEL = "WAFCON 2026"
# CAF's own press release named Channel 4 as a WAFCON broadcaster, but that
# conflicts with at least one other report saying Channel 4's AFCON deal
# doesn't extend to WAFCON - and nothing's shown up in Channel 4/E4/More4's
# actual published listings this close to kickoff. Reverted to the one
# thing every source agrees on until there's clearer confirmation either
# way; revisit if Channel 4 publish something concrete.
WATCH_PLATFORMS = "CAF TV (YouTube)"

# Morocco runs permanent Western European Summer Time (UTC+1) through the
# whole tournament window (it only reverts to standard GMT after the
# tournament ends) - kickoff times on the source page are in this zone, not
# already-converted UK time, so they need explicit conversion.
SOURCE_TZ = "Africa/Casablanca"

ROUND_HEADINGS = {
    "Group A", "Group B", "Group C", "Group D",
    "Quarter-finals", "Semi-finals", "Play-in matches", "Third place", "Final",
}


def scrape_wafcon():
    html = fetch_html(WAFCON_URL)
    return parse_wafcon_matches(html)


def parse_wafcon_matches(html: str):
    soup = BeautifulSoup(html, "lxml")
    rows = []

    current_round = None

    for el in soup.find_all(["h2", "h3", "div"]):
        if el.name in ("h2", "h3"):
            heading_text = el.get_text(strip=True)
            if heading_text in ROUND_HEADINGS:
                current_round = heading_text
            continue

        if "footballbox" not in (el.get("class") or []):
            continue

        home = el.select_one("th.fhome span[itemprop=name]")
        away = el.select_one("th.faway span[itemprop=name]")
        match_date = el.select_one(".fdate .bday")
        match_time = el.select_one(".ftime")

        if not (home and away and match_date and match_time):
            continue

        date_text = match_date.get_text(strip=True)
        time_text = match_time.get_text(strip=True)

        try:
            date_obj = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            continue

        venue_el = el.select_one(".fright [itemprop=location] [itemprop=name]")
        city_el = el.select_one(".fright [itemprop=address]")
        venue = venue_el.get_text(" ", strip=True) if venue_el else "-"
        city = city_el.get_text(" ", strip=True) if city_el else ""

        competition = (
            f"{COMPETITION_LABEL} - {current_round}" if current_round else COMPETITION_LABEL
        )

        rows.append(
            {
                "competition": competition,
                "home_team": home.get_text(" ", strip=True),
                "away_team": away.get_text(" ", strip=True),
                "kickoff_uk": to_uk_iso_from_tz(date_obj, time_text, SOURCE_TZ),
                "venue": f"{venue}, {city}" if city else venue,
                "watch_platforms": WATCH_PLATFORMS,
                "watch_notes": "",
                "official_source": WAFCON_URL,
            }
        )

    return build_df(rows)
