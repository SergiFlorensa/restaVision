from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from services.vision.geometry import (
    BoundingBox,
    FrameResolution,
    bbox_from_polygon,
    normalize_polygon,
)


@dataclass(frozen=True, slots=True)
class TableCalibration:
    table_id: str
    source_points: list[list[float]]
    normalized_points: list[list[float]]
    frame_resolution: FrameResolution
    target_width: int
    target_height: int
    homography: list[list[float]]
    roi_bbox: BoundingBox

    def __post_init__(self) -> None:
        if len(self.source_points) != 4:
            raise ValueError("source_points must contain exactly 4 points.")
        if len(self.normalized_points) != 4:
            raise ValueError("normalized_points must contain exactly 4 points.")
        if self.target_width <= 0 or self.target_height <= 0:
            raise ValueError("target dimensions must be positive.")


@dataclass(frozen=True, slots=True)
class CalibrationFile:
    version: int
    tables: list[TableCalibration]


def order_quadrilateral_points(points: list[list[float]]) -> list[list[float]]:
    if len(points) != 4:
        raise ValueError("Exactly 4 points are required.")

    matrix = np.asarray(points, dtype=float)
    sums = matrix.sum(axis=1)
    diffs = matrix[:, 0] - matrix[:, 1]
    ordered = np.array(
        [
            matrix[np.argmin(sums)],
            matrix[np.argmax(diffs)],
            matrix[np.argmax(sums)],
            matrix[np.argmin(diffs)],
        ],
        dtype=float,
    )
    if np.unique(ordered, axis=0).shape[0] != 4:
        raise ValueError("Points cannot be ordered unambiguously.")
    return ordered.tolist()


def target_rectangle_points(target_width: int, target_height: int) -> list[list[float]]:
    if target_width <= 0 or target_height <= 0:
        raise ValueError("target dimensions must be positive.")
    return [
        [0.0, 0.0],
        [float(target_width - 1), 0.0],
        [float(target_width - 1), float(target_height - 1)],
        [0.0, float(target_height - 1)],
    ]


def calculate_homography(
    source_points: list[list[float]],
    target_points: list[list[float]],
) -> np.ndarray:
    if len(source_points) != 4 or len(target_points) != 4:
        raise ValueError("source_points and target_points must contain exactly 4 points.")

    source = np.asarray(source_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if _polygon_area(source) <= 0 or _polygon_area(target) <= 0:
        raise ValueError("Homography points must form non-degenerate quadrilaterals.")

    matrix_rows: list[list[float]] = []
    for (x, y), (u, v) in zip(source, target, strict=True):
        matrix_rows.append([-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u])
        matrix_rows.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])

    _, _, vectors_t = np.linalg.svd(np.asarray(matrix_rows, dtype=float))
    homography = vectors_t[-1].reshape(3, 3)
    if abs(homography[2, 2]) < 1e-12:
        raise ValueError("Homography normalization failed.")
    return homography / homography[2, 2]


def build_table_calibration(
    table_id: str,
    source_points: list[list[float]],
    frame_resolution: FrameResolution,
    target_width: int = 500,
    target_height: int = 500,
    order_points: bool = True,
) -> TableCalibration:
    ordered_points = (
        order_quadrilateral_points(source_points)
        if order_points
        else [[float(point[0]), float(point[1])] for point in source_points]
    )
    target_points = target_rectangle_points(target_width, target_height)
    homography = calculate_homography(ordered_points, target_points)
    normalized_points = normalize_polygon(ordered_points, frame_resolution)
    return TableCalibration(
        table_id=table_id,
        source_points=ordered_points,
        normalized_points=normalized_points,
        frame_resolution=frame_resolution,
        target_width=target_width,
        target_height=target_height,
        homography=homography.tolist(),
        roi_bbox=bbox_from_polygon(ordered_points),
    )


def warp_table_view(frame: np.ndarray, calibration: TableCalibration) -> np.ndarray:
    cv2 = _load_cv2()
    homography = np.asarray(calibration.homography, dtype=float)
    return cv2.warpPerspective(
        frame,
        homography,
        (calibration.target_width, calibration.target_height),
    )


def extract_roi_view(frame: np.ndarray, bbox: BoundingBox, margin_px: int = 0) -> np.ndarray:
    if margin_px < 0:
        raise ValueError("margin_px must be non-negative.")
    height, width = frame.shape[:2]
    x_min = max(0, int(np.floor(bbox.x_min)) - margin_px)
    y_min = max(0, int(np.floor(bbox.y_min)) - margin_px)
    x_max = min(width, int(np.ceil(bbox.x_max)) + margin_px)
    y_max = min(height, int(np.ceil(bbox.y_max)) + margin_px)
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("ROI is empty.")
    return frame[y_min:y_max, x_min:x_max]


def save_calibrations(path: str | Path, calibrations: list[TableCalibration]) -> None:
    target = Path(path)
    if target.parent != Path("."):
        target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "tables": [_calibration_to_dict(calibration) for calibration in calibrations],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_calibrations(path: str | Path) -> CalibrationFile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return CalibrationFile(
        version=int(payload["version"]),
        tables=[_calibration_from_dict(item) for item in payload["tables"]],
    )


def _calibration_to_dict(calibration: TableCalibration) -> dict[str, Any]:
    payload = asdict(calibration)
    payload["frame_resolution"] = asdict(calibration.frame_resolution)
    payload["roi_bbox"] = asdict(calibration.roi_bbox)
    return payload


def _calibration_from_dict(payload: dict[str, Any]) -> TableCalibration:
    return TableCalibration(
        table_id=payload["table_id"],
        source_points=payload["source_points"],
        normalized_points=payload["normalized_points"],
        frame_resolution=FrameResolution(**payload["frame_resolution"]),
        target_width=payload["target_width"],
        target_height=payload["target_height"],
        homography=payload["homography"],
        roi_bbox=BoundingBox(**payload["roi_bbox"]),
    )


def _polygon_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for table rectification. Install requirements/ml.txt."
        ) from exc
    return cv2
