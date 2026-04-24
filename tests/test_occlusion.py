from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.events.models import EventType, TableObservation, TableState
from services.events.occlusion import OcclusionConfig, OcclusionManager, OcclusionStatus
from services.events.service import RestaurantMVPService


def test_occlusion_manager_holds_previous_count_for_short_empty_dropout() -> None:
    manager = OcclusionManager(
        OcclusionConfig(
            min_empty_observations_before_release=3,
            low_confidence_threshold=0.55,
            sudden_empty_seconds=1.0,
        )
    )
    service = RestaurantMVPService(occlusion_manager=manager)
    start = datetime(2026, 4, 24, 13, 0, tzinfo=UTC)
    service.process_observation(_observation(2, 0.96, start))

    result = service.process_observation(_observation(0, 0.92, start + timedelta(seconds=2)))

    assert result.table.state is TableState.OCCUPIED
    assert result.table.people_count == 2
    assert any(event.event_type is EventType.OCCLUSION_SUSPECTED for event in result.events)


def test_occlusion_manager_releases_after_enough_high_confidence_empty_observations() -> None:
    manager = OcclusionManager(
        OcclusionConfig(
            min_empty_observations_before_release=2,
            low_confidence_threshold=0.55,
            sudden_empty_seconds=0,
        )
    )
    service = RestaurantMVPService(occlusion_manager=manager)
    start = datetime(2026, 4, 24, 13, 0, tzinfo=UTC)
    service.process_observation(_observation(2, 0.96, start))
    first_empty = service.process_observation(_observation(0, 0.93, start + timedelta(seconds=10)))
    second_empty = service.process_observation(_observation(0, 0.94, start + timedelta(seconds=11)))

    assert first_empty.table.state is TableState.OCCUPIED
    assert second_empty.table.state is TableState.PENDING_CLEANING


def test_occlusion_manager_marks_camera_blocked_after_repeated_low_confidence_empty() -> None:
    manager = OcclusionManager(
        OcclusionConfig(
            min_empty_observations_before_release=3,
            low_confidence_threshold=0.55,
            blocked_confidence_threshold=0.15,
            blocked_observations_before_alert=2,
        )
    )
    service = RestaurantMVPService(occlusion_manager=manager)
    start = datetime(2026, 4, 24, 13, 0, tzinfo=UTC)
    service.process_observation(_observation(2, 0.96, start))
    service.process_observation(_observation(0, 0.10, start + timedelta(seconds=2)))
    result = service.process_observation(_observation(0, 0.08, start + timedelta(seconds=3)))

    camera_blocked = [
        event for event in result.events if event.event_type is EventType.CAMERA_BLOCKED
    ]
    assert result.table.state is TableState.OCCUPIED
    assert len(camera_blocked) == 1
    assert camera_blocked[0].payload_json["status"] == OcclusionStatus.CAMERA_BLOCKED.value


def _observation(people_count: int, confidence: float, observed_at: datetime) -> TableObservation:
    return TableObservation(
        camera_id="camera_mvp_01",
        zone_id="zone_table_01",
        table_id="table_01",
        people_count=people_count,
        confidence=confidence,
        observed_at=observed_at,
    )
