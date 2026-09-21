from src.bot import parse_tracker_time


def test_parse_tracker_time_handles_supabase_fractional_seconds():
    parsed = parse_tracker_time("2026-09-19T22:34:02.13346+00:00", "America/New_York")
    assert parsed.microsecond == 133460