from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from services.vision.geometry import BoundingBox, ScoredDetection


@dataclass(frozen=True, slots=True)
class LKTrackerConfig:
    max_corners_per_detection: int = 10
    quality_level: float = 0.30
    min_distance: int = 7
    block_size: int = 7
    window_size: tuple[int, int] = (15, 15)
    max_level: int = 2
    max_error: float = 30.0
    subpixel_window_size: tuple[int, int] = (5, 5)
    min_points_per_track: int = 1

    def __post_init__(self) -> None:
        if self.max_corners_per_detection < 1:
            raise ValueError("max_corners_per_detection must be greater than 0.")
        if not 0 < self.quality_level <= 1:
            raise ValueError("quality_level must be in the interval (0, 1].")
        if self.min_distance < 1:
            raise ValueError("min_distance must be greater than 0.")
        if self.block_size < 1:
            raise ValueError("block_size must be greater than 0.")
        if self.max_level < 0:
            raise ValueError("max_level must be non-negative.")
        if self.max_error < 0:
            raise ValueError("max_error must be non-negative.")
        if self.min_points_per_track < 1:
            raise ValueError("min_points_per_track must be greater than 0.")


@dataclass(frozen=True, slots=True)
class LKTrack:
    detection_id: str
    label: str | None
    points: np.ndarray
    mean_error: float

    @property
    def point_count(self) -> int:
        return int(self.points.shape[0])

    @property
    def centroid(self) -> tuple[float, float]:
        centroid = self.points.reshape(-1, 2).mean(axis=0)
        return (float(centroid[0]), float(centroid[1]))


@dataclass(frozen=True, slots=True)
class PointBoxAggregationConfig:
    padding_px: float = 5.0
    k_sigma: float = 1.5
    min_points_for_filtering: int = 3
    min_box_size_px: float = 2.0

    def __post_init__(self) -> None:
        if self.padding_px < 0:
            raise ValueError("padding_px must be non-negative.")
        if self.k_sigma <= 0:
            raise ValueError("k_sigma must be greater than 0.")
        if self.min_points_for_filtering < 1:
            raise ValueError("min_points_for_filtering must be greater than 0.")
        if self.min_box_size_px < 0:
            raise ValueError("min_box_size_px must be non-negative.")


class LKTracker:
    def __init__(self, config: LKTrackerConfig | None = None) -> None:
        self.config = config or LKTrackerConfig()
        self._previous_gray: np.ndarray | None = None
        self._tracks: dict[str, LKTrack] = {}

    def initialize_from_detections(
        self,
        frame: np.ndarray,
        detections: list[ScoredDetection],
    ) -> list[LKTrack]:
        cv2 = _load_cv2()
        gray = _to_gray(frame, cv2)
        tracks: dict[str, LKTrack] = {}

        for detection in detections:
            bbox = _clip_bbox(detection.bbox, width=gray.shape[1], height=gray.shape[0])
            if bbox is None:
                continue

            mask = np.zeros_like(gray, dtype=np.uint8)
            mask[bbox[1] : bbox[3], bbox[0] : bbox[2]] = 255
            points = cv2.goodFeaturesToTrack(
                gray,
                mask=mask,
                maxCorners=self.config.max_corners_per_detection,
                qualityLevel=self.config.quality_level,
                minDistance=self.config.min_distance,
                blockSize=self.config.block_size,
            )
            if points is None or len(points) < self.config.min_points_per_track:
                continue

            cv2.cornerSubPix(
                gray,
                points,
                self.config.subpixel_window_size,
                (-1, -1),
                (
                    cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                    30,
                    0.1,
                ),
            )
            tracks[detection.detection_id] = LKTrack(
                detection_id=detection.detection_id,
                label=detection.label,
                points=points.astype(np.float32, copy=False),
                mean_error=0.0,
            )

        self._previous_gray = gray
        self._tracks = tracks
        return list(tracks.values())

    def track(self, frame: np.ndarray) -> list[LKTrack]:
        if self._previous_gray is None or not self._tracks:
            return []

        cv2 = _load_cv2()
        gray = _to_gray(frame, cv2)
        next_tracks: dict[str, LKTrack] = {}
        lk_params = {
            "winSize": self.config.window_size,
            "maxLevel": self.config.max_level,
            "criteria": (
                cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                10,
                0.03,
            ),
        }

        for track in self._tracks.values():
            new_points, status, errors = cv2.calcOpticalFlowPyrLK(
                self._previous_gray,
                gray,
                track.points,
                None,
                **lk_params,
            )
            if new_points is None or status is None or errors is None:
                continue

            valid = (status.reshape(-1) == 1) & (errors.reshape(-1) <= self.config.max_error)
            good_points = new_points.reshape(-1, 2)[valid]
            good_errors = errors.reshape(-1)[valid]
            if len(good_points) < self.config.min_points_per_track:
                continue

            next_tracks[track.detection_id] = LKTrack(
                detection_id=track.detection_id,
                label=track.label,
                points=good_points.reshape(-1, 1, 2).astype(np.float32, copy=False),
                mean_error=float(np.mean(good_errors)) if len(good_errors) else 0.0,
            )

        self._previous_gray = gray
        self._tracks = next_tracks
        return list(next_tracks.values())

    def reset(self) -> None:
        self._previous_gray = None
        self._tracks.clear()


def tracks_to_detections(
    tracks: list[LKTrack],
    config: PointBoxAggregationConfig | None = None,
) -> list[ScoredDetection]:
    aggregation_config = config or PointBoxAggregationConfig()
    detections: list[ScoredDetection] = []
    for track in tracks:
        bbox = points_to_bounding_box(track.points, aggregation_config)
        if bbox is None:
            continue
        detections.append(
            ScoredDetection(
                detection_id=track.detection_id,
                bbox=bbox,
                score=_track_score(track),
                label=track.label,
            )
        )
    return detections


def points_to_bounding_box(
    points: np.ndarray,
    config: PointBoxAggregationConfig | None = None,
) -> BoundingBox | None:
    aggregation_config = config or PointBoxAggregationConfig()
    point_matrix = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(point_matrix) == 0:
        return None

    if len(point_matrix) >= aggregation_config.min_points_for_filtering:
        filtered_points = _filter_point_outliers(
            point_matrix,
            k_sigma=aggregation_config.k_sigma,
        )
        if len(filtered_points) > 0:
            point_matrix = filtered_points

    x_min, y_min = point_matrix.min(axis=0)
    x_max, y_max = point_matrix.max(axis=0)
    x_min -= aggregation_config.padding_px
    y_min -= aggregation_config.padding_px
    x_max += aggregation_config.padding_px
    y_max += aggregation_config.padding_px

    if (x_max - x_min) < aggregation_config.min_box_size_px:
        center_x = (x_min + x_max) / 2
        half = aggregation_config.min_box_size_px / 2
        x_min = center_x - half
        x_max = center_x + half
    if (y_max - y_min) < aggregation_config.min_box_size_px:
        center_y = (y_min + y_max) / 2
        half = aggregation_config.min_box_size_px / 2
        y_min = center_y - half
        y_max = center_y + half

    return BoundingBox(
        x_min=float(x_min),
        y_min=float(y_min),
        x_max=float(x_max),
        y_max=float(y_max),
    )


def _filter_point_outliers(points: np.ndarray, k_sigma: float) -> np.ndarray:
    centroid = points.mean(axis=0)
    std_dev = points.std(axis=0)
    safe_std = np.where(std_dev == 0, 1.0, std_dev)
    inlier_mask = np.all(np.abs(points - centroid) <= k_sigma * safe_std, axis=1)
    return points[inlier_mask]


def _track_score(track: LKTrack) -> float:
    point_factor = min(1.0, track.point_count / 10)
    error_factor = 1.0 / (1.0 + max(track.mean_error, 0.0))
    return max(0.05, min(0.99, point_factor * error_factor))


def _clip_bbox(
    bbox: BoundingBox,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    x_min = max(0, min(width, round(bbox.x_min)))
    y_min = max(0, min(height, round(bbox.y_min)))
    x_max = max(0, min(width, round(bbox.x_max)))
    y_max = max(0, min(height, round(bbox.y_max)))
    if x_max <= x_min or y_max <= y_min:
        return None
    return (x_min, y_min, x_max, y_max)


def _to_gray(frame: np.ndarray, cv2: Any) -> np.ndarray:
    matrix = np.asarray(frame)
    if matrix.ndim == 2:
        return matrix.astype(np.uint8, copy=False)
    if matrix.ndim == 3 and matrix.shape[2] >= 3:
        return cv2.cvtColor(matrix[..., :3], cv2.COLOR_BGR2GRAY)
    raise ValueError("frame must be a 2D grayscale or 3D BGR image array.")


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for LKTracker. Install requirements/ml.txt."
        ) from exc
    return cv2
