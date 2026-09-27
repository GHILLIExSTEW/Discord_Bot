from src.bot import TRACKER_UPDATE_TIMES, parse_tracker_time


def test_parse_tracker_time_handles_supabase_fractional_seconds():
    parsed = parse_tracker_time("2026-09-19T22:34:02.13346+00:00", "America/New_York")
    assert parsed.microsecond == 133460


def test_tracker_schedule_runs_at_the_top_of_each_eastern_hour():
    assert len(TRACKER_UPDATE_TIMES) == 24
    assert [(scheduled.hour, scheduled.minute) for scheduled in TRACKER_UPDATE_TIMES] == [
        (hour, 0) for hour in range(24)
    ]
    assert all(scheduled.tzinfo.key == "America/New_York" for scheduled in TRACKER_UPDATE_TIMES)