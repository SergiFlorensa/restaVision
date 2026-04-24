from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median

from services.events.models import TableObservation
from services.vision.geometry import (
    BoundingBox,
    ScoredDetection,
    assign_detections_to_zones_by_bottom_center,
    assign_detections_to_zones_by_iou,
    non_max_suppression,
)


@dataclass(frozen=True, slots=True)
class TableZone:
    zone_id: str
    table_id: str
    bbox: BoundingBox


@dataclass(frozen=True, slots=True)
class DetectionToObservationConfig:
    person_label: str = "person"
    min_detection_score: float = 0.35
    nms_iou_threshold: float = 0.50
    min_zone_iou: float = 0.05
    assignment_strategy: str = "bottom_center"
    empty_observation_confidence: float = 0.80


@dataclass(slots=True)
class TemporalCountSmoother:
    window_size: int = 5
    min_occupied_confirmations: int = 2
    min_empty_confirmations: int = 3
    _history_by_table: dict[str, deque[int]] = field(default_factory=dict)
    _stable_count_by_table: dict[str, int] = field(default_factory=dict)

    def update(self, table_id: str, raw_count: int) -> int:
        if raw_count < 0:
            raise ValueError("raw_count must be non-negative.")

        history = self._history_by_table.setdefault(
            table_id,
            deque(maxlen=self.window_size),
        )
        history.append(raw_count)

        current = self._stable_count_by_table.get(table_id, 0)
        positive_values = [count for count in history if count > 0]
        zero_count = sum(1 for count in history if count == 0)

        if positive_values and len(positive_values) >= self.min_occupied_confirmations:
            stable = int(round(median(positive_values)))
        elif current > 0 and zero_count < self.min_empty_confirmations:
            stable = current
        elif zero_count >= self.min_empty_confirmations:
            stable = 0
        else:
            stable = current

        self._stable_count_by_table[table_id] = stable
        return stable

    def reset(self, table_id: str) -> None:
        self._history_by_table.pop(table_id, None)
        self._stable_count_by_table.pop(table_id, None)


class DetectionToObservationAdapter:
    def __init__(
        self,
        zones: Iterable[TableZone],
        config: DetectionToObservationConfig | None = None,
        smoother: TemporalCountSmoother | None = None,
    ) -> None:
        self.zones = list(zones)
        self.config = config or DetectionToObservationConfig()
        self.smoother = smoother

    def build_observations(
        self,
        camera_id: str,
        detections: Iterable[ScoredDetection],
        observed_at: datetime,
    ) -> list[TableObservation]:
        person_detections = [
            detection
            for detection in detections
            if detection.score >= self.config.min_detection_score
            and detection.label == self.config.person_label
        ]
        clean_detections = non_max_suppression(
            person_detections,
            iou_threshold=self.config.nms_iou_threshold,
        )

        assignments = self._assign_detections(clean_detections)
        count_by_zone: dict[str, int] = defaultdict(int)
        scores_by_zone: dict[str, list[float]] = defaultdict(list)
        score_by_detection = {
            detection.detection_id: detection.score for detection in clean_detections
        }

        for assignment in assignments.values():
            count_by_zone[assignment.zone_id] += 1
            scores_by_zone[assignment.zone_id].append(score_by_detection[assignment.detection_id])

        observations: list[TableObservation] = []
        for zone in self.zones:
            raw_count = count_by_zone[zone.zone_id]
            people_count = (
                self.smoother.update(zone.table_id, raw_count)
                if self.smoother is not None
                else raw_count
            )
            confidence = self._observation_confidence(
                zone_id=zone.zone_id,
                raw_count=raw_count,
                people_count=people_count,
                scores=scores_by_zone[zone.zone_id],
            )
            observations.append(
                TableObservation(
                    camera_id=camera_id,
                    zone_id=zone.zone_id,
                    table_id=zone.table_id,
                    people_count=people_count,
                    confidence=confidence,
                    observed_at=observed_at,
                )
            )

        return observations

    def _assign_detections(self, detections: list[ScoredDetection]):
        detection_bboxes = {detection.detection_id: detection.bbox for detection in detections}
        zone_bboxes = {zone.zone_id: zone.bbox for zone in self.zones}

        if self.config.assignment_strategy == "iou":
            return assign_detections_to_zones_by_iou(
                detection_bboxes,
                zone_bboxes,
                min_iou=self.config.min_zone_iou,
            )
        if self.config.assignment_strategy == "bottom_center":
            return assign_detections_to_zones_by_bottom_center(detection_bboxes, zone_bboxes)
        if self.config.assignment_strategy == "hybrid":
            bottom_center_assignments = assign_detections_to_zones_by_bottom_center(
                detection_bboxes,
                zone_bboxes,
            )
            missing_detections = {
                detection_id: bbox
                for detection_id, bbox in detection_bboxes.items()
                if detection_id not in bottom_center_assignments
            }
            iou_assignments = assign_detections_to_zones_by_iou(
                missing_detections,
                zone_bboxes,
                min_iou=self.config.min_zone_iou,
            )
            return bottom_center_assignments | iou_assignments

        raise ValueError(f"Unsupported assignment strategy: {self.config.assignment_strategy}")

    def _observation_confidence(
        self,
        zone_id: str,
        raw_count: int,
        people_count: int,
        scores: list[float],
    ) -> float:
        if raw_count == 0:
            if people_count > 0:
                return min(self.config.empty_observation_confidence, 0.70)
            return self.config.empty_observation_confidence

        average_score = sum(scores) / len(scores)
        if people_count != raw_count:
            return min(average_score, 0.70)

        return average_score
