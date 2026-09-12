from datetime import datetime

from tally_logic import extract_values, period_bounds


def test_extract_values_with_keyword_and_numbers():
    text = "hours: 8 and sold 12.5 today"
    result = extract_values(text, require_keyword="hours")
    assert result == [8.0, 12.5]


def test_extract_values_ignores_non_matching_keyword():
    text = "I spent 12.5 on lunch"
    result = extract_values(text, require_keyword="hours")
    assert result == []


def test_extract_values_counts_u_marker_only():
    text = "2U US Open 🎾 / NFL 🏈"
    result = extract_values(text, require_keyword="U", pattern=r"(?i)(?<!\d)([+-]?(?:\d+(?:\.\d+)?))\s*U\b")
    assert result == [2.0]


def test_period_bounds_day_uses_midnight():
    now = datetime(2026, 9, 11, 21, 8, 0)
    start, end = period_bounds("day", now, timezone_name="America/New_York")
    assert start.hour == 0 and start.minute == 0 and start.second == 0
    assert end == now
