from __future__ import annotations

import numpy as np
from services.vision.classical import (
    ClassicalTableSignalExtractor,
    ClassicalVisionConfig,
    gaussian_blur,
    histogram_equalization,
    sobel_gradients,
    to_grayscale_uint8,
)


def test_to_grayscale_uint8_converts_bgr_image() -> None:
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    image[..., 1] = 100

    gray = to_grayscale_uint8(image)

    assert gray.shape == (2, 2)
    assert np.all(gray == 59)


def test_histogram_equalization_expands_low_contrast_range() -> None:
    image = np.array(
        [
            [10, 10, 20, 20],
            [10, 10, 20, 20],
            [30, 30, 40, 40],
            [30, 30, 40, 40],
        ],
        dtype=np.uint8,
    )

    equalized = histogram_equalization(image)

    assert equalized.min() == 0
    assert equalized.max() == 255
    assert len(np.unique(equalized)) == 4


def test_gaussian_blur_reduces_impulse_peak() -> None:
    image = np.zeros((9, 9), dtype=np.uint8)
    image[4, 4] = 255

    blurred = gaussian_blur(image, sigma=1.0)

    assert blurred[4, 4] < 255
    assert blurred[4, 4] > blurred[0, 0]


def test_sobel_gradients_detect_vertical_edge() -> None:
    image = np.zeros((8, 8), dtype=np.uint8)
    image[:, 4:] = 255

    gradients = sobel_gradients(image)

    assert gradients.magnitude[:, 3:5].mean() > gradients.magnitude[:, :2].mean()
    assert np.abs(gradients.x).max() > 0


def test_classical_table_signal_marks_edge_rich_roi_as_object_candidate() -> None:
    roi = np.zeros((20, 20), dtype=np.uint8)
    roi[5:15, 5:15] = 255
    extractor = ClassicalTableSignalExtractor(
        ClassicalVisionConfig(
            gaussian_sigma=0,
            gradient_threshold=100,
            min_edge_density=0.01,
        )
    )

    signal = extractor.extract("table_01", roi)

    assert signal.table_id == "table_01"
    assert signal.object_candidate
    assert signal.edge_density > 0
    assert signal.max_gradient > 0
