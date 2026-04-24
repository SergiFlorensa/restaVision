from __future__ import annotations

import importlib.util

import numpy as np
import pytest
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.lk_tracker import LKTracker, LKTrackerConfig

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("cv2") is None,
    reason="OpenCV is not installed.",
)


def test_lk_tracker_tracks_features_between_translated_frames() -> None:
    frame_a = np.zeros((80, 80, 3), dtype=np.uint8)
    frame_b = np.zeros((80, 80, 3), dtype=np.uint8)
    frame_a[20:40, 20:40] = 255
    frame_b[20:40, 25:45] = 255
    tracker = LKTracker(
        LKTrackerConfig(
            max_corners_per_detection=4,
            quality_level=0.01,
            min_distance=3,
            max_error=50,
        )
    )

    initial_tracks = tracker.initialize_from_detections(
        frame=frame_a,
        detections=[
            ScoredDetection(
                detection_id="person_01",
                bbox=BoundingBox(15, 15, 45, 45),
                score=0.95,
                label="person",
            )
        ],
    )
    tracked = tracker.track(frame_b)

    assert len(initial_tracks) == 1
    assert len(tracked) == 1
    assert tracked[0].detection_id == "person_01"
    assert tracked[0].centroid[0] > initial_tracks[0].centroid[0]


def test_lk_tracker_returns_empty_without_initialization() -> None:
    tracker = LKTracker()

    assert tracker.track(np.zeros((20, 20, 3), dtype=np.uint8)) == []
