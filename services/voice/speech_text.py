from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_MONTHS_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def reservation_time_for_speech(
    requested_at: datetime | None,
    fallback: str,
    *,
    timezone_name: str = "Europe/Madrid",
) -> str:
    if requested_at is None:
        return fallback
    local_value = requested_at.astimezone(ZoneInfo(timezone_name))
    month_name = _MONTHS_ES[local_value.month]
    return f"el {local_value.day} de {month_name} a las {local_value:%H:%M}"
