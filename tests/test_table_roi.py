from __future__ import annotations

import numpy as np
import pytest
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.table_roi import (
    TableRoi,
    TableRoiAnalyzer,
    extract_table_roi,
    map_roi_detections_to_frame,
    parse_table_roi,
)


class FakeDetector:
    def detect(self, frame: np.ndarray) -> list[ScoredDetection]:
        assert frame.shape[:2] == (40, 60)
        return [ScoredDetection("cup_1", BoundingBox(5, 6, 20, 24), 0.9, "cup")]


def test_extract_table_roi_returns_numpy_view_for_table_crop() -> None:
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    roi = TableRoi("table_01", BoundingBox(10, 20, 70, 60))

    extracted = extract_table_roi(frame, roi)

    assert extracted.frame.shape == (40, 60, 3)
    assert extracted.bbox == BoundingBox(10, 20, 70, 60)
    assert np.shares_memory(frame, extracted.frame)


def test_map_roi_detections_to_frame_adds_roi_offset() -> None:
    detections = [ScoredDetection("cup_1", BoundingBox(5, 6, 20, 24), 0.9, "cup")]

    mapped = map_roi_detections_to_frame(detections, BoundingBox(10, 20, 70, 60))

    assert mapped[0].detection_id == "roi_cup_1"
    assert mapped[0].bbox == BoundingBox(15, 26, 30, 44)


def test_table_roi_analyzer_detects_inside_roi_and_maps_back_to_frame() -> None:
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    analyzer = TableRoiAnalyzer(FakeDetector())
    roi = TableRoi("table_01", BoundingBox(10, 20, 70, 60))

    detections = analyzer.detect(frame, roi)

    assert detections[0].bbox == BoundingBox(15, 26, 30, 44)


def test_parse_table_roi_validates_format() -> None:
    assert parse_table_roi("10,20,70,60", table_id="table_01") == TableRoi(
        "table_01",
        BoundingBox(10, 20, 70, 60),
    )
    with pytest.raises(ValueError, match="format"):
        parse_table_roi("10,20,70", table_id="table_01")
