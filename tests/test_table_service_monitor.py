from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.table_service_monitor import TableServiceMonitor, TableServiceMonitorConfig


def detection(label: str) -> ScoredDetection:
    return ScoredDetection(label, BoundingBox(0, 0, 20, 20), 0.9, label)


def test_table_service_monitor_marks_finishing_when_empty_plates_dominate() -> None:
    monitor = TableServiceMonitor(TableServiceMonitorConfig(table_id="table_01"))

    analysis = monitor.process(
        [detection("person"), detection("plate_empty"), detection("plate_full")],
        observed_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )

    assert analysis.state == "finishing"
    assert analysis.service_flags["ready_for_checkout"] is True
    assert analysis.active_alerts[0].alert_type == "table_finishing"
    event_types = [event.event_type for event in analysis.timeline_events]
    assert "table_finishing" in event_types


def test_table_service_monitor_delays_dirty_state_after_customer_leaves() -> None:
    monitor = TableServiceMonitor(
        TableServiceMonitorConfig(table_id="table_01", dirty_grace_seconds=60)
    )
    start = datetime(2026, 4, 28, 12, 0, tzinfo=UTC)

    monitor.process([detection("person"), detection("plate_empty")], observed_at=start)
    away = monitor.process([detection("plate_empty")], observed_at=start + timedelta(seconds=30))
    dirty = monitor.process([detection("plate_empty")], observed_at=start + timedelta(seconds=91))

    assert away.state == "away"
    assert dirty.state == "dirty"
    assert dirty.service_flags["needs_cleaning"] is True
    assert dirty.active_alerts[0].alert_type == "table_dirty"
