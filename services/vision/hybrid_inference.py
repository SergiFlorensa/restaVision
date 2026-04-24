from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

import numpy as np

from services.vision.geometry import ScoredDetection
from services.vision.lk_tracker import (
    LKTrack,
    LKTracker,
    PointBoxAggregationConfig,
    tracks_to_detections,
)


class DetectionProvider(Protocol):
    def detect(self, frame: np.ndarray) -> list[ScoredDetection]: ...


class HybridInferenceMode(StrEnum):
    DETECTOR_SYNC = "detector_sync"
    LK_TRACKING = "lk_tracking"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class HybridInferenceConfig:
    detector_interval_frames: int = 10
    force_detector_after_lost: bool = True
    point_box_config: PointBoxAggregationConfig = field(default_factory=PointBoxAggregationConfig)

    def __post_init__(self) -> None:
        if self.detector_interval_frames < 1:
            raise ValueError("detector_interval_frames must be greater than 0.")


@dataclass(frozen=True, slots=True)
class HybridInferenceResult:
    detections: list[ScoredDetection]
    mode: HybridInferenceMode
    frame_index: int
    tracks: list[LKTrack] = field(default_factory=list)

    @property
    def should_reanchor(self) -> bool:
        return self.mode in {HybridInferenceMode.DETECTOR_SYNC, HybridInferenceMode.LOST}


class HybridInference:
    def __init__(
        self,
        detector: DetectionProvider,
        tracker: LKTracker | None = None,
        config: HybridInferenceConfig | None = None,
    ) -> None:
        self.detector = detector
        self.tracker = tracker or LKTracker()
        self.config = config or HybridInferenceConfig()
        self._frame_index = 0
        self._force_detector_next = True

    def process(self, frame: np.ndarray) -> HybridInferenceResult:
        self._frame_index += 1

        if self._should_run_detector():
            detections = self.detector.detect(frame)
            tracks = self.tracker.initialize_from_detections(frame, detections)
            self._force_detector_next = False
            return HybridInferenceResult(
                detections=detections,
                mode=HybridInferenceMode.DETECTOR_SYNC,
                frame_index=self._frame_index,
                tracks=tracks,
            )

        tracks = self.tracker.track(frame)
        detections = tracks_to_detections(tracks, self.config.point_box_config)
        if detections:
            return HybridInferenceResult(
                detections=detections,
                mode=HybridInferenceMode.LK_TRACKING,
                frame_index=self._frame_index,
                tracks=tracks,
            )

        if self.config.force_detector_after_lost:
            self._force_detector_next = True
        return HybridInferenceResult(
            detections=[],
            mode=HybridInferenceMode.LOST,
            frame_index=self._frame_index,
            tracks=tracks,
        )

    def force_detector_next(self) -> None:
        self._force_detector_next = True

    def reset(self) -> None:
        self._frame_index = 0
        self._force_detector_next = True
        self.tracker.reset()

    def _should_run_detector(self) -> bool:
        return (
            self._force_detector_next
            or self._frame_index % self.config.detector_interval_frames == 0
        )
