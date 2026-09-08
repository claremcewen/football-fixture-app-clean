from __future__ import annotations

from .common import fetch_html, fetch_lines, parse_wikipedia_results_grid, parse_wslfootball

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"

# wslfootball.com itself has no results view we can scrape (results only
# render client-side, confirmed - see the daily_digest_and_results memory
# notes). Wikipedia's season article has a results grid instead - scores
# only, no date once played (see parse_wikipedia_results_grid's own
# docstring), so this just returns the score half; update_results.py pairs
# it with this project's own daily-scraped fixture dates to fill in the
# other half.
WSL_RESULTS_URL = "https://en.wikipedia.org/wiki/2026%E2%80%9327_Women%27s_Super_League"


def scrape_wsl():
    lines = fetch_lines(WSL_URL)
    return parse_wsl_lines(lines)


def parse_wsl_lines(lines):
    return parse_wslfootball(lines, COMPETITION, WSL_URL)


def scrape_wsl_grid_scores() -> list[dict]:
    html = fetch_html(WSL_RESULTS_URL)
    return parse_wikipedia_results_grid(html)
