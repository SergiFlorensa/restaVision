from __future__ import annotations

import numpy as np
import pytest
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.yolo_detector import (
    YOLO_RESTAURANT_LABELS,
    YoloDetectorConfig,
    clip_bounding_box_to_frame,
    count_detections_by_label,
    detections_from_ultralytics_result,
    sanitize_detections_for_frame,
)


class FakeBoxes:
    xyxy = np.array(
        [
            [10, 20, 110, 220],
            [12, 24, 112, 224],
            [200, 20, 260, 180],
        ],
        dtype=float,
    )
    conf = np.array([0.91, 0.72, 0.88], dtype=float)
    cls = np.array([0, 0, 56], dtype=float)


class FakeResult:
    boxes = FakeBoxes()
    names = {0: "person", 56: "chair"}


def test_yolo_detector_config_validates_thresholds() -> None:
    with pytest.raises(ValueError, match="confidence_threshold"):
        YoloDetectorConfig(confidence_threshold=1.2)

    with pytest.raises(ValueError, match="iou_threshold"):
        YoloDetectorConfig(iou_threshold=-0.1)

    with pytest.raises(ValueError, match="min_box_area_ratio"):
        YoloDetectorConfig(min_box_area_ratio=1.2)


def test_detections_from_ultralytics_result_filters_person_class_and_confidence() -> None:
    detections = detections_from_ultralytics_result(
        FakeResult(),
        allowed_labels=("person",),
        min_confidence=0.8,
    )

    assert len(detections) == 1
    assert detections[0].label == "person"
    assert detections[0].score == 0.91
    assert detections[0].bbox.x_min == 10


def test_detections_from_ultralytics_result_allows_unfiltered_labels() -> None:
    detections = detections_from_ultralytics_result(
        FakeResult(),
        allowed_labels=(),
        min_confidence=0.8,
    )

    assert [detection.label for detection in detections] == ["person", "chair"]


def test_restaurant_labels_include_coco_objects_useful_for_home_table_demo() -> None:
    assert "person" in YOLO_RESTAURANT_LABELS
    assert "chair" in YOLO_RESTAURANT_LABELS
    assert "dining table" in YOLO_RESTAURANT_LABELS
    assert "cup" in YOLO_RESTAURANT_LABELS


def test_count_detections_by_label_returns_sorted_counts() -> None:
    detections = [
        ScoredDetection("d1", BoundingBox(0, 0, 10, 10), score=0.9, label="chair"),
        ScoredDetection("d2", BoundingBox(0, 0, 10, 10), score=0.9, label="person"),
        ScoredDetection("d3", BoundingBox(0, 0, 10, 10), score=0.9, label="chair"),
    ]

    assert count_detections_by_label(detections) == {"chair": 2, "person": 1}


def test_clip_bounding_box_to_frame_limits_coordinates() -> None:
    clipped = clip_bounding_box_to_frame(
        BoundingBox(x_min=-10, y_min=20, x_max=120, y_max=220),
        frame_width=100,
        frame_height=200,
    )

    assert clipped == BoundingBox(x_min=0, y_min=20, x_max=100, y_max=200)


def test_clip_bounding_box_to_frame_rejects_degenerate_box() -> None:
    clipped = clip_bounding_box_to_frame(
        BoundingBox(x_min=-30, y_min=10, x_max=-1, y_max=30),
        frame_width=100,
        frame_height=100,
    )

    assert clipped is None


def test_sanitize_detections_for_frame_filters_tiny_boxes() -> None:
    detections = [
        ScoredDetection("tiny", BoundingBox(0, 0, 5, 5), score=0.9, label="person"),
        ScoredDetection("valid", BoundingBox(-5, -5, 80, 100), score=0.8, label="person"),
    ]

    sanitized = sanitize_detections_for_frame(
        detections,
        frame_width=100,
        frame_height=100,
        min_area_ratio=0.05,
    )

    assert [detection.detection_id for detection in sanitized] == ["valid"]
    assert sanitized[0].bbox == BoundingBox(0, 0, 80, 100)
