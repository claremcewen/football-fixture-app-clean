
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

## Notes

- `Next weekend` now means the next Saturday after the current date, not the current weekend.
- `Free-to-watch only` currently treats BBC, YouTube and ITV as free platforms.
- England fixtures often have incomplete watch information, so those rows may be blank or marked TBC.

## Good next steps

1. Add more leagues (other European domestic leagues: Frauen-Bundesliga, Liga F, Serie A
   Femminile, D1 Arkema) - each is one scraper plus one line in `scripts/registry.py`.
2. Add more sports - the schema already has a `sport` column, so this is additive rather than
   a schema change.
3. Deploy to Streamlit Community Cloud (or another host) so you can use it without local Python.
