from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> list[str]:
    return FIXTURES_DIR.joinpath(filename).read_text(encoding="utf-8").splitlines()
