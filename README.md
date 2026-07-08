
# Women's Football Watch Guide

A Streamlit app that reads a generated combined fixtures file (`data/fixtures_all.csv`),
refreshed daily by scraping WSL, WSL2, England Women, UWCL and NWSL fixtures.

## Architecture

- `app.py` reads from `data/fixtures_all.csv` - no scraping or classification logic lives here.
- `scripts/update_fixtures.py` runs the 4 scrapers, classifies each row via `scripts/registry.py`,
  and rebuilds `data/fixtures_all.csv`. If a scraper errors or returns 0 rows while the previous
  file had fixtures for that competition, that competition's previous rows are kept rather than
  silently dropped - see `data/last_update_status.json` for the last run's per-source status.
- `scripts/registry.py` is the single place that maps a raw scraped `competition` label to
  `sport` / `competition_group` / `region`. Adding a new league later is one line here, not
  scattered string-matching across files.
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

## Folder structure

```text
├─ app.py
├─ requirements.txt
├─ data/
│  ├─ fixtures_all.csv
│  └─ last_update_status.json
└─ scripts/
   ├─ registry.py
   ├─ update_fixtures.py
   └─ scrapers/
      ├─ common.py
      ├─ wsl.py
      ├─ wsl2.py
      ├─ uwcl.py
      ├─ nwsl.py
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
  (WSL, WSL2, NWSL) default to just the next round, detected from actual fixture-date clustering
  rather than a fixed day count or fixed weekdays (see `next_round_window` in `app.py`) - this
  matters because leagues don't all play on the same days each week. There are two deliberately
  distinct "no specific league" entries so neither reads as the more complete option by default:
  **All (this week)** is the landing default (7-day rolling window); **All Fixtures**, at the
  bottom of the list, shows every fixture, every league, no date limit at all.
- **Club** is scoped to whichever competition is currently selected, not one long cross-league
  list - disabled for "All (this week)" (pick a league first) and for any competition in
  `NATIONAL_TEAM_COMPETITIONS` (currently just England Women - a single national team playing a
  different opponent each fixture isn't a fixed set of clubs to filter by). Enabled for
  **All Fixtures**, pulling clubs from every competition at once except the national-team ones.
- When multiple competitions have fixtures on the same day, they're ordered by
  `COMPETITION_PRIORITY` in `app.py` (defaults to WSL > WSL2 > England Women > UWCL > NWSL) so
  your most-followed league surfaces first instead of strict kickoff-time order. Adjust that
  dict directly if the priority order should change.
- **Free-to-air only (UK)** filters to BBC, ITV and YouTube.
- **Today** / **This weekend** are quick date shortcuts, underneath the Competition/Club row.
  "This weekend" is the upcoming Friday-through-Monday block (clamped so it never shows a match
  that's already passed).
- A small **"Show all upcoming"** button appears next to the status line whenever a specific
  competition is selected (not for "All (this week)") - it shows that one league's entire
  remaining schedule rather than just its next round.
- **Watch platform** and **look up a specific date** sit under a "More filters" heading, always
  visible (not a click-to-expand section) - platform filtering is valuable enough to not want it
  hidden behind an extra click.
- **Reset** clears every filter back to the "today, all competitions" default.

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

## Good next steps

1. Add more leagues (other European domestic leagues: Frauen-Bundesliga, Liga F, Serie A
   Femminile, D1 Arkema) - each is one scraper plus one line in `scripts/registry.py`.
2. Add more sports - the schema already has a `sport` column, so this is additive rather than
   a schema change.
3. Deploy to Streamlit Community Cloud (or another host) so you can use it without local Python.
