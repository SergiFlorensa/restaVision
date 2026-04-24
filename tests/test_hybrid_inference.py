from __future__ import annotations

import numpy as np
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.hybrid_inference import (
    HybridInference,
    HybridInferenceConfig,
    HybridInferenceMode,
)
from services.vision.lk_tracker import (
    LKTrack,
    PointBoxAggregationConfig,
    tracks_to_detections,
)


class FakeDetector:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, frame: np.ndarray) -> list[ScoredDetection]:
        self.calls += 1
        return [
            ScoredDetection(
                detection_id=f"person_{self.calls}",
                bbox=BoundingBox(10, 10, 30, 40),
                score=0.90,
                label="person",
            )
        ]


class FakeTracker:
    def __init__(self, tracked_batches: list[list[LKTrack]]) -> None:
        self.tracked_batches = tracked_batches
        self.initialized = 0
        self.reset_calls = 0

    def initialize_from_detections(
        self,
        frame: np.ndarray,
        detections: list[ScoredDetection],
    ) -> list[LKTrack]:
        self.initialized += 1
        return [_track(detections[0].detection_id)]

    def track(self, frame: np.ndarray) -> list[LKTrack]:
        if self.tracked_batches:
            return self.tracked_batches.pop(0)
        return []

    def reset(self) -> None:
        self.reset_calls += 1


def test_hybrid_inference_alternates_detector_and_lk_tracking() -> None:
    detector = FakeDetector()
    tracker = FakeTracker(tracked_batches=[[_track("person_1")], [_track("person_1")]])
    inference = HybridInference(
        detector=detector,
        tracker=tracker,  # type: ignore[arg-type]
        config=HybridInferenceConfig(detector_interval_frames=3),
    )
    frame = np.zeros((60, 60, 3), dtype=np.uint8)

    first = inference.process(frame)
    second = inference.process(frame)
    third = inference.process(frame)

    assert first.mode is HybridInferenceMode.DETECTOR_SYNC
    assert second.mode is HybridInferenceMode.LK_TRACKING
    assert third.mode is HybridInferenceMode.DETECTOR_SYNC
    assert detector.calls == 2


def test_hybrid_inference_forces_detector_after_lost_tracking() -> None:
    detector = FakeDetector()
    tracker = FakeTracker(tracked_batches=[[]])
    inference = HybridInference(
        detector=detector,
        tracker=tracker,  # type: ignore[arg-type]
        config=HybridInferenceConfig(detector_interval_frames=10),
    )
    frame = np.zeros((60, 60, 3), dtype=np.uint8)

    first = inference.process(frame)
    lost = inference.process(frame)
    reanchored = inference.process(frame)

    assert first.mode is HybridInferenceMode.DETECTOR_SYNC
    assert lost.mode is HybridInferenceMode.LOST
    assert reanchored.mode is HybridInferenceMode.DETECTOR_SYNC
    assert detector.calls == 2


def test_point_to_box_aggregation_filters_far_outlier() -> None:
    track = LKTrack(
        detection_id="person_1",
        label="person",
        points=np.array(
            [
                [[10.0, 10.0]],
                [[12.0, 10.0]],
                [[11.0, 12.0]],
                [[200.0, 200.0]],
            ],
            dtype=np.float32,
        ),
        mean_error=0.0,
    )

    tracked_detections = tracks_to_detections(
        [track],
        PointBoxAggregationConfig(
            padding_px=0,
            k_sigma=1.0,
            min_points_for_filtering=3,
        ),
    )

    assert tracked_detections[0].bbox.x_max < 50


def _track(detection_id: str) -> LKTrack:
    return LKTrack(
        detection_id=detection_id,
        label="person",
        points=np.array([[[10.0, 10.0]], [[20.0, 20.0]], [[25.0, 30.0]]], dtype=np.float32),
        mean_error=0.0,
    )
