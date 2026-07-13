from datetime import datetime, timedelta

from services import elapsed, format_duration


def test_elapsed_and_format_duration() -> None:
    start = datetime(2026, 1, 1, 9, 0)
    assert elapsed(start, start + timedelta(seconds=3661)) == 3661
    assert format_duration(3661) == "01:01:01"

