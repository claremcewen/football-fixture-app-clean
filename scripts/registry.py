from __future__ import annotations

# (match-prefix, sport, competition_group, region)
# Matching is "does the raw competition label start with this prefix" -
# order matters: more specific prefixes (e.g. WSL2) must come before
# shorter prefixes they'd otherwise also match (e.g. WSL).
COMPETITION_REGISTRY: list[tuple[str, str, str, str]] = [
    ("Barclays WSL2", "Football", "WSL2", "England"),
    ("Barclays WSL", "Football", "WSL", "England"),
    ("England Women", "Football", "England Women", "England"),
    ("UEFA Women's Champions League", "Football", "UWCL", "Europe"),
]


def classify(competition_label: str) -> tuple[str, str, str]:
    label = str(competition_label).strip()

    for prefix, sport, group, region in COMPETITION_REGISTRY:
        if label.startswith(prefix):
            return sport, group, region

    return "Football", label, "Unknown"
