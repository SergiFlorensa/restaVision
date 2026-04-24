from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ClassicalVisionConfig:
    gaussian_sigma: float = 1.0
    equalize_histogram: bool = False
    gradient_threshold: float = 30.0
    min_edge_density: float = 0.02
    use_canny_edges: bool = False
    canny_low_threshold: float = 40.0
    canny_high_threshold: float = 100.0
    min_canny_edge_density: float = 0.01

    def __post_init__(self) -> None:
        if self.gaussian_sigma < 0:
            raise ValueError("gaussian_sigma must be non-negative.")
        if self.gradient_threshold < 0:
            raise ValueError("gradient_threshold must be non-negative.")
        if not 0 <= self.min_edge_density <= 1:
            raise ValueError("min_edge_density must be between 0 and 1.")
        if self.canny_low_threshold < 0 or self.canny_high_threshold < 0:
            raise ValueError("Canny thresholds must be non-negative.")
        if self.canny_low_threshold > self.canny_high_threshold:
            raise ValueError("canny_low_threshold must be less than or equal to high threshold.")
        if not 0 <= self.min_canny_edge_density <= 1:
            raise ValueError("min_canny_edge_density must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class SobelGradients:
    x: np.ndarray
    y: np.ndarray
    magnitude: np.ndarray


@dataclass(frozen=True, slots=True)
class CannyEdges:
    edges: np.ndarray
    density: float


@dataclass(frozen=True, slots=True)
class HaarRectangle:
    x: int
    y: int
    width: int
    height: int
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class TableSurfaceSignal:
    table_id: str
    edge_density: float
    mean_gradient: float
    max_gradient: float
    object_candidate: bool
    canny_edge_density: float = 0.0


class ClassicalTableSignalExtractor:
    def __init__(self, config: ClassicalVisionConfig | None = None) -> None:
        self.config = config or ClassicalVisionConfig()

    def extract(self, table_id: str, roi: np.ndarray) -> TableSurfaceSignal:
        gray = to_grayscale_uint8(roi)
        if self.config.equalize_histogram:
            gray = histogram_equalization(gray)
        if self.config.gaussian_sigma > 0:
            gray = gaussian_blur(gray, sigma=self.config.gaussian_sigma)

        gradients = sobel_gradients(gray)
        strong_edges = gradients.magnitude >= self.config.gradient_threshold
        edge_density = float(np.mean(strong_edges))
        mean_gradient = float(np.mean(gradients.magnitude))
        max_gradient = float(np.max(gradients.magnitude))
        canny_edge_density = 0.0
        if self.config.use_canny_edges:
            canny = canny_edges(
                gray,
                low_threshold=self.config.canny_low_threshold,
                high_threshold=self.config.canny_high_threshold,
            )
            canny_edge_density = canny.density

        return TableSurfaceSignal(
            table_id=table_id,
            edge_density=edge_density,
            mean_gradient=mean_gradient,
            max_gradient=max_gradient,
            object_candidate=(
                edge_density >= self.config.min_edge_density
                or canny_edge_density >= self.config.min_canny_edge_density
            ),
            canny_edge_density=canny_edge_density,
        )


def to_grayscale_uint8(image: np.ndarray) -> np.ndarray:
    matrix = np.asarray(image)
    if matrix.ndim == 2:
        return _to_uint8(matrix)
    if matrix.ndim == 3 and matrix.shape[2] >= 3:
        channels = matrix[..., :3].astype(float, copy=False)
        gray = channels[..., 0] * 0.114 + channels[..., 1] * 0.587 + channels[..., 2] * 0.299
        return _to_uint8(gray)
    raise ValueError("image must be a 2D grayscale or 3D BGR image array.")


def histogram_equalization(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale_uint8(image)
    histogram = np.bincount(gray.ravel(), minlength=256)
    cdf = histogram.cumsum()
    non_zero = cdf[cdf > 0]
    if len(non_zero) == 0:
        return gray.copy()
    cdf_min = non_zero[0]
    denominator = gray.size - cdf_min
    if denominator <= 0:
        return gray.copy()

    lookup = np.round((cdf - cdf_min) * 255 / denominator)
    lookup = np.clip(lookup, 0, 255).astype(np.uint8)
    return lookup[gray]


def standardize_intensity(image: np.ndarray, epsilon: float = 1e-6) -> np.ndarray:
    if epsilon <= 0:
        raise ValueError("epsilon must be positive.")
    gray = to_grayscale_uint8(image).astype(float)
    mean = float(np.mean(gray))
    std = float(np.std(gray))
    if std < epsilon:
        return np.zeros_like(gray, dtype=float)
    return (gray - mean) / std


def gaussian_blur(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    if sigma < 0:
        raise ValueError("sigma must be non-negative.")
    gray = to_grayscale_uint8(image).astype(float)
    if sigma == 0:
        return gray.astype(np.uint8)

    kernel = _gaussian_kernel1d(sigma)
    padded_x = np.pad(gray, ((0, 0), (len(kernel) // 2, len(kernel) // 2)), mode="reflect")
    blurred_x = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), 1, padded_x)
    padded_y = np.pad(
        blurred_x,
        ((len(kernel) // 2, len(kernel) // 2), (0, 0)),
        mode="reflect",
    )
    blurred = np.apply_along_axis(
        lambda column: np.convolve(column, kernel, mode="valid"),
        0,
        padded_y,
    )
    return np.clip(np.round(blurred), 0, 255).astype(np.uint8)


def sobel_gradients(image: np.ndarray) -> SobelGradients:
    gray = to_grayscale_uint8(image).astype(float)
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=float)
    grad_x = _convolve_3x3(gray, sobel_x)
    grad_y = _convolve_3x3(gray, sobel_y)
    magnitude = np.hypot(grad_x, grad_y)
    return SobelGradients(x=grad_x, y=grad_y, magnitude=magnitude)


def canny_edges(
    image: np.ndarray,
    low_threshold: float = 40.0,
    high_threshold: float = 100.0,
    *,
    sigma: float = 1.0,
) -> CannyEdges:
    if low_threshold < 0 or high_threshold < 0:
        raise ValueError("Canny thresholds must be non-negative.")
    if low_threshold > high_threshold:
        raise ValueError("low_threshold must be less than or equal to high_threshold.")
    if sigma < 0:
        raise ValueError("sigma must be non-negative.")

    gray = to_grayscale_uint8(image)
    if sigma > 0:
        gray = gaussian_blur(gray, sigma=sigma)

    gradients = sobel_gradients(gray)
    thinned = _non_maximum_suppression(gradients.magnitude, gradients.x, gradients.y)
    edges = _hysteresis_threshold(thinned, low_threshold, high_threshold)
    return CannyEdges(edges=edges, density=float(np.mean(edges)))


def integral_image(image: np.ndarray) -> np.ndarray:
    gray = to_grayscale_uint8(image).astype(float)
    integral = np.zeros((gray.shape[0] + 1, gray.shape[1] + 1), dtype=float)
    integral[1:, 1:] = gray.cumsum(axis=0).cumsum(axis=1)
    return integral


def rectangle_sum(integral: np.ndarray, x: int, y: int, width: int, height: int) -> float:
    _validate_integral_rectangle(integral, x, y, width, height)
    x2 = x + width
    y2 = y + height
    return float(integral[y2, x2] - integral[y, x2] - integral[y2, x] + integral[y, x])


def rectangle_mean(integral: np.ndarray, x: int, y: int, width: int, height: int) -> float:
    return rectangle_sum(integral, x, y, width, height) / (width * height)


def haar_like_response(
    integral: np.ndarray,
    positive_rectangles: Sequence[HaarRectangle],
    negative_rectangles: Sequence[HaarRectangle],
    *,
    normalize: bool = True,
) -> float:
    if not positive_rectangles and not negative_rectangles:
        raise ValueError("at least one rectangle is required.")

    positive_sum, positive_area = _weighted_rectangle_total(integral, positive_rectangles)
    negative_sum, negative_area = _weighted_rectangle_total(integral, negative_rectangles)
    response = positive_sum - negative_sum
    if not normalize:
        return response

    total_area = positive_area + negative_area
    if total_area == 0:
        return 0.0
    return response / total_area


def horizontal_two_rectangle_response(
    integral: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    normalize: bool = True,
) -> float:
    if width < 2:
        raise ValueError("width must be at least 2.")
    left_width = width // 2
    right_width = width - left_width
    return haar_like_response(
        integral,
        positive_rectangles=[HaarRectangle(x=x, y=y, width=left_width, height=height)],
        negative_rectangles=[
            HaarRectangle(x=x + left_width, y=y, width=right_width, height=height)
        ],
        normalize=normalize,
    )


def vertical_two_rectangle_response(
    integral: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    normalize: bool = True,
) -> float:
    if height < 2:
        raise ValueError("height must be at least 2.")
    top_height = height // 2
    bottom_height = height - top_height
    return haar_like_response(
        integral,
        positive_rectangles=[HaarRectangle(x=x, y=y, width=width, height=top_height)],
        negative_rectangles=[
            HaarRectangle(x=x, y=y + top_height, width=width, height=bottom_height)
        ],
        normalize=normalize,
    )


def _convolve_3x3(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    padded = np.pad(image, 1, mode="edge")
    return (
        kernel[0, 0] * padded[:-2, :-2]
        + kernel[0, 1] * padded[:-2, 1:-1]
        + kernel[0, 2] * padded[:-2, 2:]
        + kernel[1, 0] * padded[1:-1, :-2]
        + kernel[1, 1] * padded[1:-1, 1:-1]
        + kernel[1, 2] * padded[1:-1, 2:]
        + kernel[2, 0] * padded[2:, :-2]
        + kernel[2, 1] * padded[2:, 1:-1]
        + kernel[2, 2] * padded[2:, 2:]
    )


def _non_maximum_suppression(
    magnitude: np.ndarray,
    grad_x: np.ndarray,
    grad_y: np.ndarray,
) -> np.ndarray:
    angle = (np.rad2deg(np.arctan2(grad_y, grad_x)) + 180) % 180
    suppressed = np.zeros_like(magnitude, dtype=float)

    center = magnitude[1:-1, 1:-1]
    angle_center = angle[1:-1, 1:-1]

    masks_and_neighbors = [
        (
            ((angle_center < 22.5) | (angle_center >= 157.5)),
            magnitude[1:-1, :-2],
            magnitude[1:-1, 2:],
        ),
        (((angle_center >= 22.5) & (angle_center < 67.5)), magnitude[:-2, 2:], magnitude[2:, :-2]),
        (
            ((angle_center >= 67.5) & (angle_center < 112.5)),
            magnitude[:-2, 1:-1],
            magnitude[2:, 1:-1],
        ),
        (
            ((angle_center >= 112.5) & (angle_center < 157.5)),
            magnitude[:-2, :-2],
            magnitude[2:, 2:],
        ),
    ]

    target = suppressed[1:-1, 1:-1]
    for direction_mask, previous, next_ in masks_and_neighbors:
        keep = direction_mask & (center >= previous) & (center >= next_)
        target[keep] = center[keep]
    return suppressed


def _hysteresis_threshold(
    magnitude: np.ndarray,
    low_threshold: float,
    high_threshold: float,
) -> np.ndarray:
    strong = magnitude >= high_threshold
    weak = (magnitude >= low_threshold) & ~strong
    edges = strong.copy()
    stack = list(zip(*np.nonzero(strong), strict=False))

    while stack:
        y, x = stack.pop()
        y0 = max(0, y - 1)
        y1 = min(magnitude.shape[0], y + 2)
        x0 = max(0, x - 1)
        x1 = min(magnitude.shape[1], x + 2)
        connected = weak[y0:y1, x0:x1] & ~edges[y0:y1, x0:x1]
        for local_y, local_x in zip(*np.nonzero(connected), strict=False):
            absolute_y = y0 + int(local_y)
            absolute_x = x0 + int(local_x)
            edges[absolute_y, absolute_x] = True
            stack.append((absolute_y, absolute_x))

    return edges


def _gaussian_kernel1d(sigma: float) -> np.ndarray:
    radius = max(1, int(np.ceil(3 * sigma)))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets**2) / (2 * sigma**2))
    return kernel / kernel.sum()


def _to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image.copy()
    return np.clip(np.round(image), 0, 255).astype(np.uint8)


def _weighted_rectangle_total(
    integral: np.ndarray,
    rectangles: Sequence[HaarRectangle],
) -> tuple[float, int]:
    total = 0.0
    area = 0
    for rectangle in rectangles:
        total += rectangle.weight * rectangle_sum(
            integral,
            rectangle.x,
            rectangle.y,
            rectangle.width,
            rectangle.height,
        )
        area += rectangle.width * rectangle.height
    return total, area


def _validate_integral_rectangle(
    integral: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    matrix = np.asarray(integral)
    if matrix.ndim != 2:
        raise ValueError("integral must be a 2D padded integral image.")
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive.")
    if x < 0 or y < 0:
        raise ValueError("x and y must be non-negative.")

    image_height = matrix.shape[0] - 1
    image_width = matrix.shape[1] - 1
    if image_height < 0 or image_width < 0:
        raise ValueError("integral must include one-pixel padding.")
    if x + width > image_width or y + height > image_height:
        raise ValueError("rectangle must fit inside the source image.")
