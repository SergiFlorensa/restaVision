from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def __post_init__(self) -> None:
        if self.x_max < self.x_min:
            raise ValueError("x_max must be greater than or equal to x_min.")
        if self.y_max < self.y_min:
            raise ValueError("y_max must be greater than or equal to y_min.")

    @classmethod
    def from_xywh(cls, x: float, y: float, width: float, height: float) -> BoundingBox:
        if width < 0:
            raise ValueError("width must be non-negative.")
        if height < 0:
            raise ValueError("height must be non-negative.")
        return cls(x_min=x, y_min=y, x_max=x + width, y_max=y + height)

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, (self.y_min + self.y_max) / 2)

    @property
    def bottom_center(self) -> tuple[float, float]:
        return ((self.x_min + self.x_max) / 2, self.y_max)

    def contains_point(self, point: tuple[float, float]) -> bool:
        x, y = point
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def intersection(self, other: BoundingBox) -> BoundingBox | None:
        x_min = max(self.x_min, other.x_min)
        y_min = max(self.y_min, other.y_min)
        x_max = min(self.x_max, other.x_max)
        y_max = min(self.y_max, other.y_max)
        if x_max <= x_min or y_max <= y_min:
            return None
        return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)

    def iou(self, other: BoundingBox) -> float:
        intersection = self.intersection(other)
        if intersection is None:
            return 0.0
        union_area = self.area + other.area - intersection.area
        if union_area <= 0:
            return 0.0
        return intersection.area / union_area


@dataclass(frozen=True, slots=True)
class ZoneAssignment:
    detection_id: str
    zone_id: str
    score: float
    strategy: str


@dataclass(frozen=True, slots=True)
class ScoredDetection:
    detection_id: str
    bbox: BoundingBox
    score: float
    label: str | None = None


@dataclass(frozen=True, slots=True)
class FrameResolution:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("width must be greater than 0.")
        if self.height <= 0:
            raise ValueError("height must be greater than 0.")

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height


@dataclass(frozen=True, slots=True)
class PolygonScaleReport:
    calibration_resolution: FrameResolution
    target_resolution: FrameResolution
    scale_x: float
    scale_y: float
    aspect_ratio_delta: float
    aspect_ratio_changed: bool


class PolygonRescaler:
    def __init__(
        self,
        calibration_resolution: FrameResolution,
        target_resolution: FrameResolution,
        max_aspect_ratio_delta: float = 0.03,
    ) -> None:
        if max_aspect_ratio_delta < 0:
            raise ValueError("max_aspect_ratio_delta must be non-negative.")
        self.calibration_resolution = calibration_resolution
        self.target_resolution = target_resolution
        self.max_aspect_ratio_delta = max_aspect_ratio_delta
        self.scale_x = target_resolution.width / calibration_resolution.width
        self.scale_y = target_resolution.height / calibration_resolution.height

    def rescale_polygon(
        self,
        points: Iterable[Iterable[float]],
        round_coordinates: bool = True,
    ) -> list[list[int]] | list[list[float]]:
        scaled_points = [
            [float(point[0]) * self.scale_x, float(point[1]) * self.scale_y] for point in points
        ]
        if not scaled_points:
            raise ValueError("Polygon must contain at least one point.")
        if round_coordinates:
            return [[round(x), round(y)] for x, y in scaled_points]
        return scaled_points

    def report(self) -> PolygonScaleReport:
        aspect_ratio_delta = abs(
            self.target_resolution.aspect_ratio - self.calibration_resolution.aspect_ratio
        )
        return PolygonScaleReport(
            calibration_resolution=self.calibration_resolution,
            target_resolution=self.target_resolution,
            scale_x=self.scale_x,
            scale_y=self.scale_y,
            aspect_ratio_delta=aspect_ratio_delta,
            aspect_ratio_changed=aspect_ratio_delta > self.max_aspect_ratio_delta,
        )


def normalize_polygon(
    points: Iterable[Iterable[float]],
    resolution: FrameResolution,
) -> list[list[float]]:
    normalized_points = [
        [float(point[0]) / resolution.width, float(point[1]) / resolution.height]
        for point in points
    ]
    if not normalized_points:
        raise ValueError("Polygon must contain at least one point.")
    return normalized_points


def denormalize_polygon(
    points: Iterable[Iterable[float]],
    resolution: FrameResolution,
    round_coordinates: bool = True,
) -> list[list[int]] | list[list[float]]:
    denormalized_points = [
        [float(point[0]) * resolution.width, float(point[1]) * resolution.height]
        for point in points
    ]
    if not denormalized_points:
        raise ValueError("Polygon must contain at least one point.")
    if round_coordinates:
        return [[round(x), round(y)] for x, y in denormalized_points]
    return denormalized_points


def same_aspect_ratio(
    first: FrameResolution,
    second: FrameResolution,
    rel_tol: float = 0.03,
) -> bool:
    if rel_tol < 0:
        raise ValueError("rel_tol must be non-negative.")
    return isclose(first.aspect_ratio, second.aspect_ratio, rel_tol=rel_tol)


def bbox_from_polygon(points: Iterable[Iterable[float]]) -> BoundingBox:
    normalized_points = [(float(point[0]), float(point[1])) for point in points]
    if not normalized_points:
        raise ValueError("Polygon must contain at least one point.")

    xs = [point[0] for point in normalized_points]
    ys = [point[1] for point in normalized_points]
    return BoundingBox(x_min=min(xs), y_min=min(ys), x_max=max(xs), y_max=max(ys))


def assign_detections_to_zones_by_iou(
    detections: Mapping[str, BoundingBox],
    zones: Mapping[str, BoundingBox],
    min_iou: float,
) -> dict[str, ZoneAssignment]:
    if min_iou < 0:
        raise ValueError("min_iou must be non-negative.")

    assignments: dict[str, ZoneAssignment] = {}
    for detection_id, detection_bbox in detections.items():
        best_zone_id: str | None = None
        best_score = 0.0
        for zone_id, zone_bbox in zones.items():
            score = detection_bbox.iou(zone_bbox)
            if score > best_score:
                best_zone_id = zone_id
                best_score = score

        if best_zone_id is not None and best_score >= min_iou:
            assignments[detection_id] = ZoneAssignment(
                detection_id=detection_id,
                zone_id=best_zone_id,
                score=best_score,
                strategy="iou",
            )

    return assignments


def assign_detections_to_zones_by_bottom_center(
    detections: Mapping[str, BoundingBox],
    zones: Mapping[str, BoundingBox],
) -> dict[str, ZoneAssignment]:
    assignments: dict[str, ZoneAssignment] = {}
    for detection_id, detection_bbox in detections.items():
        point = detection_bbox.bottom_center
        for zone_id, zone_bbox in zones.items():
            if zone_bbox.contains_point(point):
                assignments[detection_id] = ZoneAssignment(
                    detection_id=detection_id,
                    zone_id=zone_id,
                    score=1.0,
                    strategy="bottom_center",
                )
                break
    return assignments


def non_max_suppression(
    detections: Iterable[ScoredDetection],
    iou_threshold: float,
) -> list[ScoredDetection]:
    if iou_threshold < 0 or iou_threshold > 1:
        raise ValueError("iou_threshold must be between 0 and 1.")

    pending = sorted(detections, key=lambda detection: detection.score, reverse=True)
    kept: list[ScoredDetection] = []

    while pending:
        current = pending.pop(0)
        kept.append(current)
        pending = [
            candidate
            for candidate in pending
            if current.label != candidate.label or current.bbox.iou(candidate.bbox) <= iou_threshold
        ]

    return kept
