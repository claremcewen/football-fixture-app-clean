from __future__ import annotations

# (match-prefix, sport, competition_group, region, tier)
# Matching is "does the raw competition label start with this prefix" -
# order matters: more specific prefixes (e.g. WSL2) must come before
# shorter prefixes they'd otherwise also match (e.g. WSL).
# tier is the English women's football pyramid level ("Tier 1".."Tier 4"),
# or None for competitions outside that pyramid (internationals, European
# club competitions, other countries' leagues).
COMPETITION_REGISTRY: list[tuple[str, str, str, str, str | None]] = [
    ("Barclays WSL2", "Football", "WSL2", "England", "Tier 2"),
    ("Barclays WSL", "Football", "WSL", "England", "Tier 1"),
    ("England Women", "Football", "England Women", "England", None),
    ("UEFA Women's Champions League", "Football", "UWCL", "Europe", None),
    ("NWSL", "Football", "NWSL", "USA", None),
    ("Northern Premier Division", "Football", "Northern Premier Division", "England", "Tier 3"),
    ("Southern Premier Division", "Football", "Southern Premier Division", "England", "Tier 3"),
    ("Division 1 North", "Football", "Division 1 North", "England", "Tier 4"),
    ("Division 1 Midlands", "Football", "Division 1 Midlands", "England", "Tier 4"),
    ("Division 1 South East", "Football", "Division 1 South East", "England", "Tier 4"),
    ("Division 1 South West", "Football", "Division 1 South West", "England", "Tier 4"),
    # Cross-divisional cup - open to both tier 3 and tier 4 clubs, so it
    # doesn't belong to a single tier the way the six league divisions do.
    ("The FA Women's National League Cup", "Football", "FAWNL Cup", "England", None),
    # Competition label includes the round/group, e.g. "WAFCON 2026 - Group A".
    ("WAFCON", "Football", "WAFCON", "Africa", None),
    # Scotland's top flight - tier is England-pyramid-only, so None here even
    # though SWPL 1 is itself a country's top division.
    ("SWPL 1", "Football", "SWPL 1", "Scotland", None),
]


def classify(competition_label: str) -> tuple[str, str, str, str | None]:
    label = str(competition_label).strip()

    for prefix, sport, group, region, tier in COMPETITION_REGISTRY:
        if label.startswith(prefix):
            return sport, group, region, tier

    return "Football", label, "Unknown", None
