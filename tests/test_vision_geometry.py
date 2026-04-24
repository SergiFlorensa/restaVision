from __future__ import annotations

from services.vision.geometry import (
    BoundingBox,
    FrameResolution,
    PolygonRescaler,
    ScoredDetection,
    assign_detections_to_zones_by_bottom_center,
    assign_detections_to_zones_by_iou,
    bbox_from_polygon,
    denormalize_polygon,
    non_max_suppression,
    normalize_polygon,
    same_aspect_ratio,
)


def test_bounding_box_iou_handles_overlap_and_no_overlap() -> None:
    left = BoundingBox(0, 0, 100, 100)
    right = BoundingBox(50, 50, 150, 150)
    separate = BoundingBox(200, 200, 250, 250)

    assert round(left.iou(right), 4) == 0.1429
    assert left.iou(separate) == 0.0


def test_bbox_from_polygon_extracts_enclosing_box() -> None:
    bbox = bbox_from_polygon([[10, 20], [80, 15], [90, 70], [15, 75]])

    assert bbox == BoundingBox(10, 15, 90, 75)


def test_assign_detections_to_zones_by_iou_chooses_best_zone() -> None:
    detections = {
        "person_01": BoundingBox(20, 20, 80, 120),
        "person_02": BoundingBox(250, 20, 330, 120),
    }
    zones = {
        "table_a": BoundingBox(0, 0, 150, 150),
        "table_b": BoundingBox(200, 0, 380, 150),
    }

    assignments = assign_detections_to_zones_by_iou(detections, zones, min_iou=0.05)

    assert assignments["person_01"].zone_id == "table_a"
    assert assignments["person_02"].zone_id == "table_b"


def test_assign_detections_by_bottom_center_handles_large_table_zones() -> None:
    detections = {
        "person_01": BoundingBox(30, 20, 70, 130),
        "person_02": BoundingBox(300, 20, 340, 130),
    }
    zones = {
        "table_a": BoundingBox(0, 100, 150, 180),
        "table_b": BoundingBox(250, 100, 380, 180),
    }

    assignments = assign_detections_to_zones_by_bottom_center(detections, zones)

    assert assignments["person_01"].zone_id == "table_a"
    assert assignments["person_02"].zone_id == "table_b"


def test_non_max_suppression_removes_lower_scored_duplicate_detections() -> None:
    detections = [
        ScoredDetection("high", BoundingBox(0, 0, 100, 100), score=0.95, label="person"),
        ScoredDetection("duplicate", BoundingBox(5, 5, 105, 105), score=0.72, label="person"),
        ScoredDetection("other", BoundingBox(200, 0, 260, 100), score=0.60, label="person"),
    ]

    kept = non_max_suppression(detections, iou_threshold=0.5)

    assert [detection.detection_id for detection in kept] == ["high", "other"]


def test_polygon_rescaler_maps_calibration_points_to_current_resolution() -> None:
    rescaler = PolygonRescaler(
        calibration_resolution=FrameResolution(width=1920, height=1080),
        target_resolution=FrameResolution(width=1280, height=720),
    )

    polygon = rescaler.rescale_polygon([[0, 0], [960, 540], [1920, 1080]])

    assert polygon == [[0, 0], [640, 360], [1280, 720]]
    assert not rescaler.report().aspect_ratio_changed


def test_polygon_rescaler_flags_aspect_ratio_change() -> None:
    rescaler = PolygonRescaler(
        calibration_resolution=FrameResolution(width=1024, height=768),
        target_resolution=FrameResolution(width=1280, height=720),
    )

    report = rescaler.report()

    assert report.aspect_ratio_changed
    assert not same_aspect_ratio(report.calibration_resolution, report.target_resolution)


def test_polygon_normalization_round_trip() -> None:
    resolution = FrameResolution(width=1280, height=720)
    normalized = normalize_polygon([[0, 0], [640, 360], [1280, 720]], resolution)

    restored = denormalize_polygon(normalized, resolution)

    assert normalized == [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]]
    assert restored == [[0, 0], [640, 360], [1280, 720]]
