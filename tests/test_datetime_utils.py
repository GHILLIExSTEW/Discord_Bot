from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.datetime_utils import parse_iso_datetime


@pytest.mark.parametrize("fraction", ["4", "42", "423", "4232", "42324", "423240"])
@pytest.mark.parametrize("offset", ["Z", "+00:00", "-04:00"])
def test_fractional_seconds_are_normalized_for_python310(fraction, offset):
    value = f"2026-10-02T10:25:23.{fraction}{offset}"
    expected_offset = "+00:00" if offset == "Z" else offset
    expected = f"2026-10-02T10:25:23.{fraction.ljust(6, '0')}{expected_offset}"
    with patch("src.datetime_utils.datetime", wraps=datetime) as parser:
        result = parse_iso_datetime(value)
        parser.fromisoformat.assert_called_once_with(expected)
    assert result == datetime.fromisoformat(expected)


def test_reported_postgres_timestamp_preserves_microseconds():
    assert parse_iso_datetime("2026-10-02T10:25:23.42324+00:00") == datetime(
        2026, 10, 2, 10, 25, 23, 423240, tzinfo=timezone.utc,
    )


def test_timestamp_without_fraction_is_preserved():
    assert parse_iso_datetime("2026-10-02T10:25:23Z") == datetime(
        2026, 10, 2, 10, 25, 23, tzinfo=timezone.utc,
    )


def test_invalid_timestamp_is_not_hidden():
    with pytest.raises(ValueError):
        parse_iso_datetime("invalid")
