
# Women's Football Watch Guide

A Streamlit app that reads a generated combined fixtures file (`data/fixtures_all.csv`),
refreshed daily by scraping WSL, WSL2, England Women, UWCL, NWSL and FAWNL (tiers 3-4) fixtures.

## Architecture

- `app.py` reads from `data/fixtures_all.csv` - no scraping or classification logic lives here.
- `scripts/update_fixtures.py` runs the 4 scrapers, classifies each row via `scripts/registry.py`,
  and rebuilds `data/fixtures_all.csv`. If a scraper errors or returns 0 rows while the previous
  file had fixtures for that competition, that competition's previous rows are kept rather than
  silently dropped - see `data/last_update_status.json` for the last run's per-source status.
- `scripts/registry.py` is the single place that maps a raw scraped `competition` label to
  `sport` / `competition_group` / `region` / `tier`. Adding a new league later is one line here,
  not scattered string-matching across files. `tier` is the English women's football pyramid
  level ("Tier 1".."Tier 4"); `None` for competitions outside that pyramid (internationals,
  European club competitions, other countries' leagues).
- `scripts/update_fixtures.py`'s `TASKS` list normally maps one scraper to one competition_group,
  but a task can cover several (see FAWNL below) - each entry lists which competition_group
  values it's responsible for, used for per-source fallback matching when a scraper fails.
- `scripts/scrapers/` - each scraper splits `fetch_*` (network call) from `parse_*_lines`
  (pure text parsing), so parsing can be unit tested without hitting the network.
- `scripts/scrapers/tests/` - pytest suite. Each source has a small hand-built "populated"
  fixture (`*_sample.txt`) that exercises the row-extraction logic deterministically, plus a
  real captured snapshot (`*_live.txt`) checked for parse-without-crashing. Run with:
  ```bash
  pytest scripts/scrapers/tests/
  ```
  Refresh the live snapshots with `python -m scripts.scrapers.tests.capture_fixtures`.
- `.github/workflows/update.fixtures.yml` runs the updater daily, and if any source failed or
  fell back to stale data, opens/updates a single GitHub issue titled "Fixture scraper failures"
  summarizing what happened (reused across runs, not one issue per day).
- `scripts/scrapers/nwsl.py` has a static `NWSL_TEAM_VENUES` lookup (team -> home stadium),
  since NWSL is a single round-robin and the scraped source doesn't list venue. Update this if a
  team relocates or a new team joins; unmapped teams fall back to `"-"`.
- `scripts/scrapers/nwsl.py` has a `STOP_MARKERS` set, same pattern as `wsl.py`/`wsl2.py` - the
  last match in the scraped list is immediately followed by page footer/nav content rather than
  another time/date line, so without a stop marker that footer gets read as the last match's
  watch platforms.
- `scripts/scrapers/fawnl.py` covers all six FAWNL tier 3/4 divisions (Northern Premier, Southern
  Premier, Division 1 North/Midlands/South East/South West) plus the FAWNL Cup in one scraper,
  since one API call returns all of them at once (the FAWNL Plate is not currently included - no
  fixtures exist for it yet; Plates typically only populate once Cup early-round results are
  known). Unlike the other sources, this isn't HTML text-scraping - the official site
  (`wnl.thefa.com`) renders fixtures via JavaScript, but there's a clean public JSON API behind
  it (`api.wnl.thefa.com/matches`, needs an `X-TENANT-ID: wnl` header, no authentication). This
  is more reliable than any of the text-based scrapers - structured data straight from the FA's
  system rather than parsed page text - but it's an internal/undocumented API, so it could
  change without notice; if it ever breaks, that's the first thing to check.
- Venue isn't available anywhere in the FAWNL API for any of the ~88 clubs (checked directly),
  so unlike NWSL there's nothing to derive automatically. Instead of a hardcoded Python dict,
  home grounds live in `data/fawnl_venues.csv` (`team,venue` columns, one row per club, blank
  until confirmed) - `fawnl.py`'s `load_venue_lookup()` reads it at scrape time. Don't guess
  entries from general knowledge; many of these clubs share a name with an unrelated men's club
  playing at a completely different ground - fill this in only with confirmed grounds.

## Folder structure

```text
├─ app.py
├─ requirements.txt
├─ data/
│  ├─ fixtures_all.csv
│  ├─ last_update_status.json
│  └─ fawnl_venues.csv
└─ scripts/
   ├─ registry.py
   ├─ update_fixtures.py
   └─ scrapers/
      ├─ common.py
      ├─ wsl.py
      ├─ wsl2.py
      ├─ uwcl.py
      ├─ nwsl.py
      ├─ fawnl.py
      ├─ internationals.py
      └─ tests/
```

## First run

Install packages:

```bash
pip install -r requirements.txt
```

Update the fixture file:

```bash
python scripts/update_fixtures.py
```

Run the app:

```bash
streamlit run app.py
```

## What to expect

- The app should run immediately because a tiny sample `data/fixtures_all.csv` is included.
- Running `update_fixtures.py` should overwrite that file with fresh data from the official source pages.
- If one scraper fails or returns 0 rows, the updater keeps that competition's previous
  fixtures instead of dropping them, and records what happened in
  `data/last_update_status.json`.

## Using the app

Page layout, top to bottom: last-updated timestamp, a status line showing what's currently in
view, the Competition / Club / Free-to-air controls, quick date-shortcut buttons, a "More
filters" section, then the fixture list.

- The app opens on **today, across all competitions** - if nothing's on today, it falls back to
  showing the next 7 days instead of a blank screen.
- The **status line** ("Showing ... fixtures ...") reflects whatever the controls below it are
  currently set to - it sits above them since it's really a summary of their combined effect.
- Picking a **Competition** auto-selects a sensible view for that league: sparse/international
  competitions (England Women, UWCL) default to showing everything upcoming; weekly leagues
  (WSL, WSL2, NWSL, all six FAWNL divisions) default to just the next round, detected from actual
  fixture-date clustering rather than a fixed day count or fixed weekdays (see
  `next_round_window` in `app.py`) - this matters because leagues don't all play on the same days
  each week. There are two deliberately distinct "no specific league" entries so neither reads as
  the more complete option by default: **All (this week)** is the landing default (7-day rolling
  window); **All Fixtures**, at the bottom of the list, shows every fixture, every league, no
  date limit at all.
- FAWNL divisions are labeled with their English pyramid tier in the dropdown (e.g.
  "Tier 3 — Northern Premier Division") - `COMPETITION_DISPLAY_ORDER` in `app.py` groups the
  list by tier instead of alphabetically, and the tier label itself is read from the data's own
  `tier` column (via `format_func` on the selectbox) rather than a separate hardcoded mapping, so
  it can't drift out of sync with `registry.py`.
- **Club** is scoped to whichever competition is currently selected, not one long cross-league
  list - disabled for "All (this week)" (pick a league first) and for any competition in
  `NATIONAL_TEAM_COMPETITIONS` (currently just England Women - a single national team playing a
  different opponent each fixture isn't a fixed set of clubs to filter by). Enabled for
  **All Fixtures**, pulling clubs from every competition at once except the national-team ones.
- When multiple competitions have fixtures on the same day, they're ordered by
  `COMPETITION_PRIORITY` in `app.py` (defaults to WSL > WSL2 > FAWNL tier 3 > FAWNL tier 4 >
  England Women > UWCL > NWSL) so your most-followed league surfaces first instead of strict
  kickoff-time order. Adjust that dict directly if the priority order should change.
- **Free-to-air only (UK)** filters to BBC, ITV and YouTube.
- **Today** / **This weekend** / **Next 7 Days** are quick date shortcuts, underneath the
  Competition/Club row. "This weekend" is the upcoming Friday-through-Monday block (clamped so
  it never shows a match that's already passed); "Next 7 Days" is a plain rolling 7-day window
  from today, independent of whatever Competition is currently selected.
- A small **"Show all upcoming"** button appears next to the status line whenever a specific
  competition is selected (not for "All (this week)") - it shows that one league's entire
  remaining schedule rather than just its next round.
- **Watch platform** and **look up a specific date** sit under a "More filters" heading, always
  visible (not a click-to-expand section) - platform filtering is valuable enough to not want it
  hidden behind an extra click.
- **Reset** clears Competition, Club, Watch platform and Free-to-air back to their defaults, but
  deliberately leaves whatever date/view you're currently on alone (e.g. "This weekend" stays
  selected) - it's a filters reset, not a full return to the landing state.

## Visual design

The app is branded as **She Can Kick It** (`shecankickit.com`, linked in the footer). Brand
colors and fonts live as constants near the top of `app.py`:
- `BRAND_GREEN` `#7ED957`, `BRAND_DARK_BLUE` `#145B8E`, `BRAND_MID_BLUE` `#0597B2`,
  `BRAND_CREAM` `#FAF2E9`.
- Fonts: **Anton** for headings/brand title, **Montserrat** for body text - loaded via Google
  Fonts in `APP_CSS`.
- `.streamlit/config.toml` sets the base Streamlit theme (page background, primary accent,
  text color) to match; `APP_CSS` handles everything Streamlit's theme system doesn't reach
  (card styling, status banner, headings, footer link).
- The logo lives at `assets/logo.png`, used as both the browser tab favicon (`page_icon` in
  `st.set_page_config`) and the header image. It already has "She Can Kick It" lettering baked
  into the graphic, so the header shows the logo image only, not a duplicate text title.

Match cards separately show a small colored dot per competition (`COMPETITION_COLOR` in
`app.py`) purely for at-a-glance grouping. This is a **different, original palette - not
official league/team branding or logos** - deliberately, to stay clear of any trademark
concerns, and deliberately kept distinct from the She Can Kick It brand colors above so the two
color systems (brand identity vs. competition grouping) don't get confused with each other. Add
a new hex value there when a new competition is added; unlisted ones fall back to a neutral gray
(`DEFAULT_COMPETITION_COLOR`).

Styling is done via a single injected `<style>` block (`APP_CSS` in `app.py`) plus small render
helper functions (`render_status`, `render_date_heading`, `render_section_heading`) rather than
Streamlit's built-in `st.info`/`st.markdown("##...")`, to get a more compact, on-brand look than
Streamlit's defaults.

Any user-facing card content built from scraped data goes through `html.escape()` before being
interpolated into raw HTML (`match_card` uses `st.markdown(..., unsafe_allow_html=True)`) -
necessary since this content comes from third-party sites, not just internal data.

## Notes

- England fixtures often have incomplete watch information, so those rows may be blank or marked TBC.
- FAWNL fixtures (league divisions and Cup) never have watch platform info (not televised) and
  show `-` for venue until `data/fawnl_venues.csv` is filled in.
- The FAWNL Plate isn't included yet - no fixtures exist for it in the API as of 2026-07,
  probably because Plate competitions typically only populate once Cup early-round results are
  known. Check back once the Cup's first round or two has been played.
- The Adobe Women's FA Cup (the main all-tiers FA Cup, not FAWNL's internal Cup) is tracked
  separately on `thefa.com` directly, a different platform from `wnl.thefa.com` - not
  investigated yet. 2026/27 rounds run Sunday 23 August 2026 (Preliminary Round) through the
  Final on 15 May 2027; worth checking `thefa.com/competitions/the-womens-fa-cup/fixtures` once
  fixtures for FAWNL-tier clubs are actually posted.

## Good next steps

1. Add more leagues (other European domestic leagues: Frauen-Bundesliga, Liga F, Serie A
   Femminile, D1 Arkema) - each is one scraper plus one line in `scripts/registry.py`.
2. Add more sports - the schema already has a `sport` column, so this is additive rather than
   a schema change.
3. Deploy to Streamlit Community Cloud (or another host) so you can use it without local Python.
4. Fill in `data/fawnl_venues.csv` as home grounds are confirmed.
5. Add the Adobe Women's FA Cup once its fixtures are live (see Notes above).
6. Add the FAWNL Plate once it has fixtures.
