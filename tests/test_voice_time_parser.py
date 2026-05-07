from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from services.voice.time_parser import parse_reservation_time


def test_parse_today_two_midday_as_fourteen_hundred_not_two_am_next_day() -> None:
    parsed = parse_reservation_time(
        "hoy a las dos de mediodia",
        reference=datetime(2026, 5, 6, 12, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert parsed is not None
    assert parsed.requested_at.isoformat().startswith("2026-05-06T14:00:00")


def test_parse_two_in_the_afternoon_as_fourteen_hundred() -> None:
    parsed = parse_reservation_time(
        "a las dos de la tarde",
        reference=datetime(2026, 5, 6, 10, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert parsed is not None
    assert parsed.requested_at.isoformat().startswith("2026-05-06T14:00:00")
