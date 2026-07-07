from __future__ import annotations

from .common import build_df, fetch_lines, parse_day_header, TIME_RE, to_uk_iso

WSL_URL = "https://www.wslfootball.com/fixtures/wsl"
COMPETITION = "Barclays WSL"

STOP_MARKERS = {
    "© 2025 Women's Super League Football Ltd. All rights reserved.",
    "Back to top",
    "Privacy Settings & Cookie Management",
}


def _is_team_code(line: str) -> bool:
    return len(line) <= 4 and line.isupper()


def _is_watch_line(line: str) -> bool:
    watch_terms = ["Sky Sports", "BBC", "YouTube"]
    return any(term.lower() in line.lower() for term in watch_terms)


def scrape_wsl():
    lines = fetch_lines(WSL_URL)
    return parse_wsl_lines(lines)


def parse_wsl_lines(lines):
    rows = []

    current_date = None
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        if line in STOP_MARKERS:
            break

        parsed_date = parse_day_header(line)
        if parsed_date:
            current_date = parsed_date
            i += 1
            continue

        # Match structure:
        # sport-match-details-for
        # Home Team
        # VS
        # Away Team
        # 12:00 PM
        if (
            current_date
            and line == "sport-match-details-for"
            and i + 4 < len(lines)
            and lines[i + 2].strip() == "VS"
            and TIME_RE.match(lines[i + 4].strip())
        ):
            home_team = lines[i + 1].strip()
            away_team = lines[i + 3].strip()
            time_text = lines[i + 4].strip()

            venue = "TBC"
            watch_platforms = []

            j = i + 5
            while j < len(lines):
                next_line = lines[j].strip()

                if not next_line:
                    j += 1
                    continue

                if next_line in STOP_MARKERS:
                    break
                if parse_day_header(next_line):
                    break
                if next_line == "sport-match-details-for":
                    break

                if venue == "TBC":
                    if (
                        next_line not in {home_team, away_team}
                        and not _is_team_code(next_line)
                        and not _is_watch_line(next_line)
                        and next_line not in {"VS", "fixtures", "results", "Calendar", "clubs"}
                    ):
                        venue = next_line
                        j += 1
                        continue

                if _is_watch_line(next_line) and next_line not in watch_platforms:
                    watch_platforms.append(next_line)

                j += 1

            rows.append(
                {
                    "competition": COMPETITION,
                    "home_team": home_team,
                    "away_team": away_team,
                    "kickoff_uk": to_uk_iso(current_date, time_text),
                    "venue": venue,
                    "watch_platforms": ", ".join(watch_platforms),
                    "watch_notes": "",
                    "official_source": WSL_URL,
                }
            )

            i = j
            continue

        i += 1

    return build_df(rows)