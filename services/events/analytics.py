from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from services.events.models import TableSession


@dataclass(frozen=True, slots=True)
class TableDurationSummary:
    table_id: str
    closed_session_count: int
    total_duration_seconds: int
    average_duration_seconds: float
    min_duration_seconds: int
    max_duration_seconds: int


def summarize_closed_session_durations(
    sessions: list[TableSession],
) -> list[TableDurationSummary]:
    durations_by_table: dict[str, list[int]] = {}
    for session in sessions:
        if session.duration_seconds is None:
            continue
        if session.duration_seconds < 0:
            raise ValueError("session.duration_seconds must be non-negative.")
        durations_by_table.setdefault(session.table_id, []).append(session.duration_seconds)

    return [
        TableDurationSummary(
            table_id=table_id,
            closed_session_count=len(durations),
            total_duration_seconds=sum(durations),
            average_duration_seconds=float(mean(durations)),
            min_duration_seconds=min(durations),
            max_duration_seconds=max(durations),
        )
        for table_id, durations in sorted(durations_by_table.items())
    ]


def average_closed_session_duration_seconds(
    sessions: list[TableSession],
    table_id: str | None = None,
) -> float | None:
    durations = [
        session.duration_seconds
        for session in sessions
        if session.duration_seconds is not None
        and (table_id is None or session.table_id == table_id)
    ]
    if not durations:
        return None
    if any(duration < 0 for duration in durations):
        raise ValueError("session.duration_seconds must be non-negative.")
    return float(mean(durations))
