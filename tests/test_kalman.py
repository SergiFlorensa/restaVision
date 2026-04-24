from __future__ import annotations

from services.vision.geometry import BoundingBox
from services.vision.kalman import (
    BoundingBoxKalmanSmoother,
    ConstantVelocityKalmanFilter,
    Kalman2DConfig,
)


def test_constant_velocity_kalman_filter_predicts_through_dropout() -> None:
    tracker = ConstantVelocityKalmanFilter(
        initial_position=(0.0, 0.0),
        config=Kalman2DConfig(process_noise=0.1, measurement_noise=1.0),
    )

    tracker.step((10.0, 0.0), dt_seconds=1.0)
    estimate = tracker.step(None, dt_seconds=1.0)

    assert estimate.corrected_with_measurement is False
    assert estimate.x > 10.0
    assert abs(estimate.y) < 1.0


def test_bounding_box_smoother_keeps_bbox_during_short_dropout() -> None:
    smoother = BoundingBoxKalmanSmoother(
        config=Kalman2DConfig(process_noise=0.1, measurement_noise=4.0)
    )

    first = smoother.step(BoundingBox(0, 0, 10, 20), dt_seconds=1.0)
    second = smoother.step(BoundingBox(10, 0, 20, 20), dt_seconds=1.0)
    dropout = smoother.step(None, dt_seconds=1.0)

    assert first is not None
    assert second is not None
    assert dropout is not None
    assert abs(dropout.width - second.width) < 1e-9
    assert abs(dropout.height - second.height) < 1e-9
    assert dropout.center[0] > second.center[0]


def test_bounding_box_smoother_reduces_center_jitter() -> None:
    smoother = BoundingBoxKalmanSmoother(
        config=Kalman2DConfig(process_noise=0.01, measurement_noise=80.0),
        size_smoothing=0.2,
    )
    raw_boxes = [
        BoundingBox(90, 0, 110, 20),
        BoundingBox(100, 0, 120, 20),
        BoundingBox(82, 0, 102, 20),
        BoundingBox(98, 0, 118, 20),
        BoundingBox(86, 0, 106, 20),
    ]

    smoothed_centers = [
        smoother.step(bbox, dt_seconds=1.0).center[0]  # type: ignore[union-attr]
        for bbox in raw_boxes
    ]
    raw_centers = [bbox.center[0] for bbox in raw_boxes]

    assert max(smoothed_centers) - min(smoothed_centers) < max(raw_centers) - min(raw_centers)
