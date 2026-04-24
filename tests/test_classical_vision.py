from __future__ import annotations

import numpy as np
from services.vision.classical import (
    ClassicalTableSignalExtractor,
    ClassicalVisionConfig,
    HaarRectangle,
    canny_edges,
    gaussian_blur,
    haar_like_response,
    histogram_equalization,
    horizontal_two_rectangle_response,
    integral_image,
    rectangle_mean,
    rectangle_sum,
    sobel_gradients,
    standardize_intensity,
    to_grayscale_uint8,
    vertical_two_rectangle_response,
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


def test_standardize_intensity_returns_zero_mean_unit_variance() -> None:
    image = np.array([[10, 20], [30, 40]], dtype=np.uint8)

    standardized = standardize_intensity(image)

    assert np.isclose(float(np.mean(standardized)), 0.0)
    assert np.isclose(float(np.std(standardized)), 1.0)


def test_standardize_intensity_handles_constant_image() -> None:
    image = np.full((4, 4), 80, dtype=np.uint8)

    standardized = standardize_intensity(image)

    assert np.all(standardized == 0.0)


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


def test_canny_edges_extracts_connected_rectangle_boundary() -> None:
    image = np.zeros((32, 32), dtype=np.uint8)
    image[8:24, 8:24] = 255

    edges = canny_edges(image, low_threshold=20, high_threshold=60, sigma=0)

    assert edges.edges.dtype == bool
    assert edges.density > 0
    assert edges.edges[8:24, 8:24].any()
    assert not edges.edges[:4, :4].any()


def test_canny_edges_rejects_invalid_threshold_order() -> None:
    image = np.zeros((8, 8), dtype=np.uint8)

    try:
        canny_edges(image, low_threshold=100, high_threshold=50)
    except ValueError as exc:
        assert "low_threshold" in str(exc)
    else:
        raise AssertionError("Expected canny_edges to reject inverted thresholds.")


def test_integral_image_computes_rectangle_sum_and_mean() -> None:
    image = np.arange(1, 17, dtype=np.uint8).reshape(4, 4)

    integral = integral_image(image)

    assert integral.shape == (5, 5)
    assert rectangle_sum(integral, x=1, y=1, width=2, height=2) == float(image[1:3, 1:3].sum())
    assert rectangle_mean(integral, x=1, y=1, width=2, height=2) == float(image[1:3, 1:3].mean())


def test_rectangle_sum_rejects_out_of_bounds_regions() -> None:
    integral = integral_image(np.zeros((3, 3), dtype=np.uint8))

    try:
        rectangle_sum(integral, x=2, y=2, width=2, height=1)
    except ValueError as exc:
        assert "fit inside" in str(exc)
    else:
        raise AssertionError("Expected rectangle_sum to reject an out-of-bounds region.")


def test_haar_like_response_measures_weighted_region_contrast() -> None:
    image = np.zeros((4, 4), dtype=np.uint8)
    image[:, :2] = 100
    integral = integral_image(image)

    response = haar_like_response(
        integral,
        positive_rectangles=[HaarRectangle(x=0, y=0, width=2, height=4)],
        negative_rectangles=[HaarRectangle(x=2, y=0, width=2, height=4)],
    )

    assert response == 50.0


def test_two_rectangle_responses_detect_horizontal_and_vertical_contrast() -> None:
    horizontal = np.zeros((4, 4), dtype=np.uint8)
    horizontal[:, :2] = 100
    vertical = np.zeros((4, 4), dtype=np.uint8)
    vertical[:2, :] = 80

    assert horizontal_two_rectangle_response(integral_image(horizontal), 0, 0, 4, 4) == 50.0
    assert vertical_two_rectangle_response(integral_image(vertical), 0, 0, 4, 4) == 40.0


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


def test_classical_table_signal_can_use_canny_density_as_candidate_signal() -> None:
    roi = np.zeros((32, 32), dtype=np.uint8)
    roi[8:24, 8:24] = 255
    extractor = ClassicalTableSignalExtractor(
        ClassicalVisionConfig(
            gaussian_sigma=0,
            gradient_threshold=10_000,
            min_edge_density=1.0,
            use_canny_edges=True,
            canny_low_threshold=20,
            canny_high_threshold=60,
            min_canny_edge_density=0.001,
        )
    )

    signal = extractor.extract("table_01", roi)

    assert signal.object_candidate
    assert signal.canny_edge_density > 0
