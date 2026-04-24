from __future__ import annotations

from datetime import UTC, datetime

from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.observation_adapter import (
    DetectionToObservationAdapter,
    DetectionToObservationConfig,
    TableZone,
    TemporalCountSmoother,
)


def test_detection_to_observation_adapter_counts_people_by_table_zone() -> None:
    adapter = DetectionToObservationAdapter(
        zones=[
            TableZone("zone_a", "table_a", BoundingBox(0, 100, 200, 220)),
            TableZone("zone_b", "table_b", BoundingBox(250, 100, 450, 220)),
        ],
        config=DetectionToObservationConfig(assignment_strategy="bottom_center"),
    )

    observations = adapter.build_observations(
        camera_id="camera_01",
        observed_at=datetime(2026, 4, 21, 18, 0, tzinfo=UTC),
        detections=[
            ScoredDetection("p1", BoundingBox(40, 20, 90, 160), 0.93, "person"),
            ScoredDetection("p2", BoundingBox(110, 30, 160, 170), 0.91, "person"),
            ScoredDetection("p3", BoundingBox(300, 20, 360, 170), 0.89, "person"),
        ],
    )

    count_by_table = {
        observation.table_id: observation.people_count for observation in observations
    }
    assert count_by_table == {"table_a": 2, "table_b": 1}


def test_detection_to_observation_adapter_applies_nms_before_counting() -> None:
    adapter = DetectionToObservationAdapter(
        zones=[TableZone("zone_a", "table_a", BoundingBox(0, 0, 200, 220))],
        config=DetectionToObservationConfig(
            assignment_strategy="bottom_center",
            nms_iou_threshold=0.50,
        ),
    )

    observations = adapter.build_observations(
        camera_id="camera_01",
        observed_at=datetime(2026, 4, 21, 18, 0, tzinfo=UTC),
        detections=[
            ScoredDetection("p1", BoundingBox(40, 20, 110, 180), 0.94, "person"),
            ScoredDetection("p1_duplicate", BoundingBox(42, 22, 112, 182), 0.80, "person"),
        ],
    )

    assert observations[0].people_count == 1


def test_temporal_count_smoother_holds_count_through_short_camera_dropout() -> None:
    smoother = TemporalCountSmoother(
        window_size=4,
        min_occupied_confirmations=2,
        min_empty_confirmations=3,
    )

    assert smoother.update("table_a", 2) == 0
    assert smoother.update("table_a", 2) == 2
    assert smoother.update("table_a", 0) == 2
    assert smoother.update("table_a", 0) == 2
    assert smoother.update("table_a", 0) == 0


def test_adapter_can_emit_smoothed_observation_instead_of_raw_dropout() -> None:
    adapter = DetectionToObservationAdapter(
        zones=[TableZone("zone_a", "table_a", BoundingBox(0, 100, 200, 220))],
        smoother=TemporalCountSmoother(
            window_size=4,
            min_occupied_confirmations=2,
            min_empty_confirmations=3,
        ),
    )
    observed_at = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)
    occupied_detection = [ScoredDetection("p1", BoundingBox(40, 20, 90, 160), 0.93, "person")]

    first_observation = adapter.build_observations("camera_01", occupied_detection, observed_at)[0]
    second_observation = adapter.build_observations("camera_01", occupied_detection, observed_at)[0]

    assert first_observation.people_count == 0
    assert second_observation.people_count == 1

    dropout = adapter.build_observations("camera_01", [], observed_at)[0]
    assert dropout.people_count == 1
    assert dropout.confidence == 0.70
