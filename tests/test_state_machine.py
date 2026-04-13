from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.events.models import EventType, TableObservation, TableState
from services.events.service import RestaurantMVPService


def test_table_flow_from_ready_to_clean_ready() -> None:
    service = RestaurantMVPService()
    start = datetime(2026, 4, 13, 10, 0, tzinfo=timezone.utc)

    first = service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=2,
            confidence=0.98,
            observed_at=start,
        )
    )
    assert first.table.state is TableState.OCCUPIED
    assert first.session is not None
    assert first.prediction is not None
    assert {event.event_type for event in first.events} >= {
        EventType.PEOPLE_COUNTED,
        EventType.TABLE_OCCUPIED,
        EventType.SESSION_STARTED,
        EventType.TABLE_STATE_CHANGED,
    }

    second = service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=1,
            confidence=0.96,
            observed_at=start + timedelta(minutes=25),
        )
    )
    assert second.table.state is TableState.FINALIZING
    assert second.session is not None
    assert {event.event_type for event in second.events} >= {
        EventType.PEOPLE_COUNTED,
        EventType.EXIT_FROM_TABLE,
        EventType.TABLE_STATE_CHANGED,
    }

    third = service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=0,
            confidence=0.97,
            observed_at=start + timedelta(minutes=40),
        )
    )
    assert third.table.state is TableState.PENDING_CLEANING
    assert third.session is None
    assert {event.event_type for event in third.events} >= {
        EventType.PEOPLE_COUNTED,
        EventType.TABLE_RELEASED,
        EventType.SESSION_ENDED,
        EventType.TABLE_PENDING_CLEANING,
        EventType.TABLE_STATE_CHANGED,
    }

    ready = service.mark_table_ready("table_01", observed_at=start + timedelta(minutes=43))
    assert ready.state is TableState.READY

    sessions = service.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].duration_seconds == 2400
    assert sessions[0].final_status == TableState.PENDING_CLEANING.value


def test_eta_uses_historical_session_after_first_cycle() -> None:
    service = RestaurantMVPService()
    start = datetime(2026, 4, 13, 11, 0, tzinfo=timezone.utc)

    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=2,
            confidence=0.98,
            observed_at=start,
        )
    )
    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=0,
            confidence=0.98,
            observed_at=start + timedelta(minutes=30),
        )
    )
    service.mark_table_ready("table_01", observed_at=start + timedelta(minutes=31))

    follow_up = service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=2,
            confidence=0.99,
            observed_at=start + timedelta(minutes=60),
        )
    )

    assert follow_up.prediction is not None
    assert follow_up.prediction.explanation.startswith("ETA baseline basada")
    assert follow_up.prediction.value == 1800

