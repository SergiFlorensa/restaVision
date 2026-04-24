from __future__ import annotations

import numpy as np
from services.vision.calibration import (
    build_table_calibration,
    calculate_homography,
    extract_roi_view,
    load_calibrations,
    order_quadrilateral_points,
    save_calibrations,
    target_rectangle_points,
)
from services.vision.geometry import BoundingBox, FrameResolution


def test_order_quadrilateral_points_returns_clockwise_starting_top_left() -> None:
    points = [[100, 100], [10, 10], [100, 10], [10, 100]]

    ordered = order_quadrilateral_points(points)

    assert ordered == [[10.0, 10.0], [100.0, 10.0], [100.0, 100.0], [10.0, 100.0]]


def test_calculate_homography_maps_source_rectangle_to_target_rectangle() -> None:
    source_points = [[10, 20], [110, 20], [110, 70], [10, 70]]
    target_points = target_rectangle_points(101, 51)

    homography = calculate_homography(source_points, target_points)
    mapped = _apply_homography(homography, np.asarray(source_points, dtype=float))

    assert np.allclose(mapped, np.asarray(target_points), atol=1e-6)


def test_build_table_calibration_persists_normalized_points_and_homography(tmp_path) -> None:
    calibration = build_table_calibration(
        table_id="table_01",
        source_points=[[10, 20], [110, 20], [110, 70], [10, 70]],
        frame_resolution=FrameResolution(width=200, height=100),
        target_width=101,
        target_height=51,
    )
    target = tmp_path / "calibrations.json"

    save_calibrations(target, [calibration])
    loaded = load_calibrations(target)

    assert loaded.version == 1
    assert loaded.tables[0].table_id == "table_01"
    assert loaded.tables[0].normalized_points == [
        [0.05, 0.2],
        [0.55, 0.2],
        [0.55, 0.7],
        [0.05, 0.7],
    ]
    assert loaded.tables[0].roi_bbox == BoundingBox(10, 20, 110, 70)


def test_extract_roi_view_uses_numpy_view_not_copy() -> None:
    frame = np.zeros((20, 30, 3), dtype=np.uint8)

    roi = extract_roi_view(frame, BoundingBox(5, 4, 15, 14))
    roi[:, :] = 255

    assert np.shares_memory(frame, roi)
    assert frame[4:14, 5:15].mean() == 255


def _apply_homography(homography: np.ndarray, points: np.ndarray) -> np.ndarray:
    homogeneous = np.column_stack([points, np.ones(points.shape[0])])
    mapped = (homography @ homogeneous.T).T
    mapped = mapped[:, :2] / mapped[:, 2:3]
    return mapped
