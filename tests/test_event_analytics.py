from __future__ import annotations

from datetime import UTC, datetime

from services.events.analytics import (
    average_closed_session_duration_seconds,
    summarize_closed_session_durations,
)
from services.events.models import TableSession


def test_summarize_closed_session_durations_groups_by_table() -> None:
    sessions = [
        _session("s1", "table_01", 1200),
        _session("s2", "table_01", 1800),
        _session("s3", "table_02", 600),
        _session("open", "table_01", None),
    ]

    summaries = summarize_closed_session_durations(sessions)

    assert len(summaries) == 2
    assert summaries[0].table_id == "table_01"
    assert summaries[0].closed_session_count == 2
    assert summaries[0].average_duration_seconds == 1500
    assert summaries[0].total_duration_seconds == 3000
    assert summaries[1].table_id == "table_02"
    assert summaries[1].average_duration_seconds == 600


def test_average_closed_session_duration_can_filter_by_table() -> None:
    sessions = [
        _session("s1", "table_01", 1200),
        _session("s2", "table_02", 600),
    ]

    assert average_closed_session_duration_seconds(sessions) == 900
    assert average_closed_session_duration_seconds(sessions, table_id="table_02") == 600
    assert average_closed_session_duration_seconds(sessions, table_id="missing") is None


def _session(session_id: str, table_id: str, duration: int | None) -> TableSession:
    return TableSession(
        session_id=session_id,
        table_id=table_id,
        start_ts=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
        duration_seconds=duration,
    )
