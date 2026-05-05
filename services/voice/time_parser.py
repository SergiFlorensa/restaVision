from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_TIME_WORDS = {
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuna": 21,
    "veintiuno": 21,
    "veintidos": 22,
    "veintitres": 23,
}


@dataclass(frozen=True, slots=True)
class ParsedReservationTime:
    requested_at: datetime
    display_text: str
    parser: str


@dataclass(frozen=True, slots=True)
class ParsedReservationDate:
    requested_date: date
    display_text: str
    parser: str


def parse_reservation_time(
    text: str,
    *,
    reference: datetime,
    preferred_date: date | None = None,
    timezone_name: str = "Europe/Madrid",
) -> ParsedReservationTime | None:
    text = _normalize_spanish_text(text)
    local_reference = _to_local(reference, timezone_name)
    manual = _parse_manual_spanish_time(
        text,
        reference=local_reference,
        preferred_date=preferred_date,
        timezone_name=timezone_name,
    )
    if manual is not None:
        return manual
    if not _has_explicit_time_signal(text):
        return None
    return _parse_with_dateparser(text, reference=local_reference, timezone_name=timezone_name)


def parse_reservation_date(
    text: str,
    *,
    reference: datetime,
    timezone_name: str = "Europe/Madrid",
) -> ParsedReservationDate | None:
    text = _normalize_spanish_text(text)
    local_reference = _to_local(reference, timezone_name)
    date_offset = _relative_day_offset(text)
    weekday_offset = _weekday_offset(text, local_reference)
    if weekday_offset is not None:
        date_offset = weekday_offset
    if date_offset > 0 or "hoy" in text:
        requested_date = (local_reference + timedelta(days=date_offset)).date()
        return ParsedReservationDate(
            requested_date=requested_date,
            display_text=requested_date.strftime("%d/%m/%Y"),
            parser="manual_spanish",
        )
    return _parse_date_with_dateparser(text, reference=local_reference, timezone_name=timezone_name)


def _parse_with_dateparser(
    text: str,
    *,
    reference: datetime,
    timezone_name: str,
) -> ParsedReservationTime | None:
    try:
        from dateparser.search import search_dates
    except ModuleNotFoundError:
        return None

    settings = {
        "DATE_ORDER": "DMY",
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": reference,
        "TIMEZONE": timezone_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "DEFAULT_LANGUAGES": ["es"],
        "PREFER_DAY_OF_MONTH": "first",
    }
    matches = search_dates(text, languages=["es"], settings=settings) or []
    for raw_text, parsed in matches:
        if not _looks_like_reservation_time(raw_text):
            continue
        requested_at = _to_local(parsed, timezone_name)
        if requested_at < reference:
            requested_at += timedelta(days=1)
        return ParsedReservationTime(
            requested_at=requested_at,
            display_text=_format_reservation_datetime(requested_at),
            parser="dateparser",
        )
    return None


def _parse_date_with_dateparser(
    text: str,
    *,
    reference: datetime,
    timezone_name: str,
) -> ParsedReservationDate | None:
    try:
        from dateparser.search import search_dates
    except ModuleNotFoundError:
        return None

    settings = {
        "DATE_ORDER": "DMY",
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": reference,
        "TIMEZONE": timezone_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "DEFAULT_LANGUAGES": ["es"],
        "REQUIRE_PARTS": ["day"],
    }
    matches = search_dates(text, languages=["es"], settings=settings) or []
    for raw_text, parsed in matches:
        if _has_explicit_time_signal(raw_text) or not _looks_like_date_signal(raw_text):
            continue
        requested_date = _to_local(parsed, timezone_name).date()
        return ParsedReservationDate(
            requested_date=requested_date,
            display_text=requested_date.strftime("%d/%m/%Y"),
            parser="dateparser",
        )
    return None


def _parse_manual_spanish_time(
    text: str,
    *,
    reference: datetime,
    preferred_date: date | None,
    timezone_name: str,
) -> ParsedReservationTime | None:
    time_match = re.search(r"\b([01]?\d|2[0-3])(?::|\.|h)(\d{2})\b", text)
    if not time_match:
        time_match = re.search(
            r"\b(?:a las|a los|a la|sobre las|sobre los|para las|para los)\s+"
            r"([01]?\d|2[0-3])\b",
            text,
        )
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
    else:
        word_match = re.search(
            r"\b(?:a las|a los|a la|sobre las|sobre los|para las|para los)\s+"
            r"(una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|"
            r"trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|"
            r"veinte|veintiuna|veintiuno|veintidos|veintitres)"
            r"(?:\s+y\s+(media|cuarto))?\b",
            text,
        )
        if not word_match:
            return None
        hour = _TIME_WORDS[word_match.group(1)]
        if hour < 12 and "medio dia" not in text and "mediodia" not in text:
            hour += 12
        minute = 30 if word_match.group(2) == "media" else 15 if word_match.group(2) else 0

    date_offset = _relative_day_offset(text)
    weekday_offset = _weekday_offset(text, reference)
    if weekday_offset is not None:
        date_offset = weekday_offset
    if date_offset == 0 and weekday_offset is None and preferred_date is not None:
        requested_at = datetime.combine(
            preferred_date,
            time(hour=hour, minute=minute),
            tzinfo=ZoneInfo(timezone_name),
        )
    else:
        requested_at = reference.replace(hour=hour, minute=minute, second=0, microsecond=0)
        requested_at += timedelta(days=date_offset)
    if date_offset == 0 and requested_at < reference:
        requested_at += timedelta(days=1)
    if requested_at.tzinfo is None:
        requested_at = requested_at.replace(tzinfo=ZoneInfo(timezone_name))
    return ParsedReservationTime(
        requested_at=requested_at,
        display_text=_format_reservation_datetime(requested_at),
        parser="manual_spanish",
    )


def _relative_day_offset(text: str) -> int:
    if "pasado manana" in text:
        return 2
    if "manana" in text:
        return 1
    if "hoy" in text:
        return 0
    return 0


def _weekday_offset(text: str, reference: datetime) -> int | None:
    weekdays = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "domingo": 6,
    }
    for word, target in weekdays.items():
        if re.search(rf"\b{word}\b", text):
            offset = (target - reference.weekday()) % 7
            return offset if offset > 0 else 7
    return None


def _looks_like_reservation_time(raw_text: str) -> bool:
    return bool(
        re.search(r"\d", raw_text)
        or any(
            marker in raw_text.lower()
            for marker in (
                "hoy",
                "manana",
                "pasado",
                "lunes",
                "martes",
                "miercoles",
                "jueves",
                "viernes",
                "sabado",
                "domingo",
            )
        )
    )


def _looks_like_date_signal(raw_text: str) -> bool:
    text = _normalize_spanish_text(raw_text)
    return any(
        marker in text
        for marker in (
            "hoy",
            "manana",
            "pasado",
            "lunes",
            "martes",
            "miercoles",
            "jueves",
            "viernes",
            "sabado",
            "domingo",
        )
    )


def _has_explicit_time_signal(text: str) -> bool:
    text = _normalize_spanish_text(text)
    return bool(
        re.search(r"\b([01]?\d|2[0-3])(?::|\.|h)(\d{2})\b", text)
        or re.search(
            r"\b(?:a las|a los|a la|sobre las|sobre los|para las|para los)\s+"
            r"([01]?\d|2[0-3])\b",
            text,
        )
        or re.search(
            r"\b(?:a las|a los|a la|sobre las|sobre los|para las|para los)\s+"
            r"(una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|"
            r"trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|"
            r"veinte|veintiuna|veintiuno|veintidos|veintitres)\b",
            text,
        )
    )


def _to_local(value: datetime, timezone_name: str) -> datetime:
    timezone = ZoneInfo(timezone_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _format_reservation_datetime(value: datetime) -> str:
    local_value = value.astimezone(ZoneInfo("Europe/Madrid"))
    return local_value.strftime("%d/%m/%Y %H:%M")


def _normalize_spanish_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip()
