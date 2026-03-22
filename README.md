
# Women's Football Watch Guide — Phase 2 remake

This remake keeps the same basic Streamlit app, but restructures the project around a generated combined fixtures file.

## What changed

- `app.py` now reads from `data/fixtures_all.csv`
- `scripts/update_fixtures.py` rebuilds that file automatically
- starter scrapers are included for:
  - Barclays WSL
  - Barclays WSL2
  - England Women senior fixtures

## Folder structure

```text
wfw_phase2_remade/
├─ app.py
├─ requirements.txt
├─ data/
│  └─ fixtures_all.csv
└─ scripts/
   ├─ update_fixtures.py
   └─ scrapers/
      ├─ common.py
      ├─ wsl.py
      ├─ wsl2.py
      └─ internationals.py
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
- If one scraper fails, the updater will still save whatever data it successfully collected.

## Notes

- `Next weekend` now means the next Saturday after the current date, not the current weekend.
- `Free-to-watch only` currently treats BBC, YouTube and ITV as free platforms.
- England fixtures often have incomplete watch information, so those rows may be blank or marked TBC.

## Good next steps

1. Add more international teams or tournaments.
2. Add a GitHub Actions workflow to run `update_fixtures.py` every day.
3. Deploy to Streamlit Community Cloud so you can use it on Android without local Python.
