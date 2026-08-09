from __future__ import annotations

from scripts.update_fixtures import is_suspicious_drop


def test_sharp_drop_from_meaningful_previous_count_is_suspicious():
    # wslfootball.com's real incident: 175 previous, only 10 returned.
    assert is_suspicious_drop(row_count=10, previous_count=175) is True


def test_gradual_decline_is_not_suspicious():
    # A normal day-to-day decline as matches get played and drop off.
    assert is_suspicious_drop(row_count=170, previous_count=175) is False


def test_small_previous_count_is_never_flagged():
    # Competitions with few fixtures (e.g. England Women) shouldn't trigger
    # on ordinary small-number noise.
    assert is_suspicious_drop(row_count=0, previous_count=2) is False
    assert is_suspicious_drop(row_count=1, previous_count=5) is False


def test_increase_is_not_suspicious():
    assert is_suspicious_drop(row_count=200, previous_count=175) is False


def test_exactly_at_threshold_is_not_suspicious():
    # 50% of 20 is 10 - the check is strictly less-than, so exactly half
    # should not trip it.
    assert is_suspicious_drop(row_count=10, previous_count=20) is False


def test_just_below_threshold_is_suspicious():
    assert is_suspicious_drop(row_count=9, previous_count=20) is True
