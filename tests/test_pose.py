from __future__ import annotations

import numpy as np
import pytest
from services.vision.pose import YoloPoseConfig, draw_pose_detections, poses_from_ultralytics_result


class FakeBoxes:
    xyxy = np.array([[10, 20, 90, 180]], dtype=np.float32)
    conf = np.array([0.88], dtype=np.float32)


class FakeKeypoints:
    xy = np.array(
        [
            [
                [40, 30],
                [38, 28],
                [42, 28],
                [35, 32],
                [45, 32],
                [30, 70],
                [60, 70],
                [25, 105],
                [65, 105],
                [20, 135],
                [70, 135],
                [35, 130],
                [55, 130],
                [35, 165],
                [55, 165],
                [35, 178],
                [55, 178],
            ]
        ],
        dtype=np.float32,
    )
    conf = np.ones((1, 17), dtype=np.float32)


class FakeResult:
    boxes = FakeBoxes()
    keypoints = FakeKeypoints()


def test_yolo_pose_config_validates_cpu_friendly_thresholds() -> None:
    with pytest.raises(ValueError, match="keypoint_confidence"):
        YoloPoseConfig(keypoint_confidence_threshold=1.5)


def test_poses_from_ultralytics_result_extracts_keypoints() -> None:
    poses = poses_from_ultralytics_result(
        FakeResult(),
        frame_width=120,
        frame_height=200,
        min_confidence=0.3,
        min_keypoint_confidence=0.3,
    )

    assert len(poses) == 1
    assert poses[0].bbox.x_min == 10
    assert len(poses[0].keypoints) == 17
    assert poses[0].keypoints[0].name == "nose"


def test_draw_pose_detections_draws_without_box_requirement() -> None:
    frame = np.zeros((200, 120, 3), dtype=np.uint8)
    poses = poses_from_ultralytics_result(
        FakeResult(),
        frame_width=120,
        frame_height=200,
        min_confidence=0.3,
        min_keypoint_confidence=0.3,
    )

    output = draw_pose_detections(frame, poses, draw_boxes=False, draw_silhouette=True)

    assert output.shape == frame.shape
    assert int(output.sum()) > 0
