from __future__ import annotations

from services.vision.detection_policy import DetectionPolicy, TemporalEvidenceAccumulator
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.table_service_monitor import TableServiceMonitor, TableServiceMonitorConfig


def test_restaurant_detection_policy_uses_class_specific_thresholds() -> None:
    policy = DetectionPolicy()
    detections = [
        ScoredDetection("person_low", BoundingBox(0, 0, 20, 80), 0.40, "person"),
        ScoredDetection("fork_ok", BoundingBox(0, 0, 10, 10), 0.23, "fork"),
        ScoredDetection("knife_low", BoundingBox(0, 0, 10, 10), 0.20, "knife"),
    ]

    filtered = policy.filter_detections(detections, frame_width=200, frame_height=200)

    assert [detection.detection_id for detection in filtered] == ["fork_ok"]


def test_temporal_evidence_confirms_small_service_objects_after_repeated_hits() -> None:
    policy = DetectionPolicy()
    accumulator = TemporalEvidenceAccumulator(policy)
    fork = ScoredDetection("fork", BoundingBox(0, 0, 10, 10), 0.40, "fork")

    first = accumulator.update([fork])
    second = accumulator.update([fork])
    third = accumulator.update([fork])

    assert first.stable_counts == {}
    assert second.stable_counts == {}
    assert third.stable_counts == {"fork": 1}


def test_table_service_monitor_can_use_stable_counts_instead_of_raw_frame_noise() -> None:
    monitor = TableServiceMonitor(
        TableServiceMonitorConfig(table_id="table_01", require_plate=False, require_knife=False)
    )
    raw_detections = [
        ScoredDetection("person", BoundingBox(0, 0, 20, 80), 0.90, "person"),
        ScoredDetection("fork", BoundingBox(0, 0, 10, 10), 0.25, "fork"),
    ]

    analysis = monitor.process(raw_detections, stable_counts={"person": 1})

    assert analysis.people_count == 1
    assert analysis.object_counts == {"person": 1}
    assert analysis.missing_items == {"fork": 1}
