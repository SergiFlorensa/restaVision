from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from services.vision.geometry import BoundingBox, ScoredDetection


class FrameDetector(Protocol):
    def detect(self, frame: np.ndarray) -> list[ScoredDetection]: ...


@dataclass(frozen=True, slots=True)
class TableRoi:
    table_id: str
    bbox: BoundingBox
    margin_ratio: float = 0.0

    def __post_init__(self) -> None:
        if not self.table_id:
            raise ValueError("table_id must not be empty.")
        if not 0 <= self.margin_ratio <= 1:
            raise ValueError("margin_ratio must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class ExtractedTableRoi:
    table_id: str
    frame: np.ndarray
    bbox: BoundingBox


class TableRoiAnalyzer:
    """Runs detailed object detection only inside a table crop."""

    def __init__(self, detector: FrameDetector) -> None:
        self.detector = detector

    def detect(self, frame: np.ndarray, roi: TableRoi | None) -> list[ScoredDetection]:
        if roi is None:
            return self.detector.detect(frame)

        extracted = extract_table_roi(frame, roi)
        if extracted.frame.size == 0:
            return []
        detections = self.detector.detect(extracted.frame)
        return map_roi_detections_to_frame(detections, extracted.bbox)


def extract_table_roi(frame: np.ndarray, roi: TableRoi) -> ExtractedTableRoi:
    if frame.ndim < 2:
        raise ValueError("frame must have at least two dimensions.")
    frame_height, frame_width = frame.shape[:2]
    bbox = _clamp_roi_bbox(roi.bbox, frame_width, frame_height, roi.margin_ratio)
    x1 = int(round(bbox.x_min))
    y1 = int(round(bbox.y_min))
    x2 = int(round(bbox.x_max))
    y2 = int(round(bbox.y_max))
    return ExtractedTableRoi(table_id=roi.table_id, frame=frame[y1:y2, x1:x2], bbox=bbox)


def map_roi_detections_to_frame(
    detections: list[ScoredDetection],
    roi_bbox: BoundingBox,
) -> list[ScoredDetection]:
    mapped: list[ScoredDetection] = []
    for detection in detections:
        bbox = BoundingBox(
            x_min=detection.bbox.x_min + roi_bbox.x_min,
            y_min=detection.bbox.y_min + roi_bbox.y_min,
            x_max=detection.bbox.x_max + roi_bbox.x_min,
            y_max=detection.bbox.y_max + roi_bbox.y_min,
        )
        mapped.append(
            ScoredDetection(
                detection_id=f"roi_{detection.detection_id}",
                bbox=bbox,
                score=detection.score,
                label=detection.label,
            )
        )
    return mapped


def parse_table_roi(value: str | None, table_id: str, margin_ratio: float = 0.0) -> TableRoi | None:
    if value is None or not value.strip():
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("roi must use the format x_min,y_min,x_max,y_max.")
    try:
        x_min, y_min, x_max, y_max = (float(part) for part in parts)
    except ValueError as exc:
        raise ValueError("roi coordinates must be numeric.") from exc
    return TableRoi(
        table_id=table_id,
        bbox=BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max),
        margin_ratio=margin_ratio,
    )


def _clamp_roi_bbox(
    bbox: BoundingBox,
    frame_width: int,
    frame_height: int,
    margin_ratio: float,
) -> BoundingBox:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive.")
    margin_x = bbox.width * margin_ratio
    margin_y = bbox.height * margin_ratio
    x_min = min(max(bbox.x_min - margin_x, 0.0), float(frame_width))
    y_min = min(max(bbox.y_min - margin_y, 0.0), float(frame_height))
    x_max = min(max(bbox.x_max + margin_x, 0.0), float(frame_width))
    y_max = min(max(bbox.y_max + margin_y, 0.0), float(frame_height))
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("roi must overlap the frame with positive area.")
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)
