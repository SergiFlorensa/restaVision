from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ClassicalVisionConfig:
    gaussian_sigma: float = 1.0
    equalize_histogram: bool = False
    gradient_threshold: float = 30.0
    min_edge_density: float = 0.02

    def __post_init__(self) -> None:
        if self.gaussian_sigma < 0:
            raise ValueError("gaussian_sigma must be non-negative.")
        if self.gradient_threshold < 0:
            raise ValueError("gradient_threshold must be non-negative.")
        if not 0 <= self.min_edge_density <= 1:
            raise ValueError("min_edge_density must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class SobelGradients:
    x: np.ndarray
    y: np.ndarray
    magnitude: np.ndarray


@dataclass(frozen=True, slots=True)
class TableSurfaceSignal:
    table_id: str
    edge_density: float
    mean_gradient: float
    max_gradient: float
    object_candidate: bool


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
        return TableSurfaceSignal(
            table_id=table_id,
            edge_density=edge_density,
            mean_gradient=mean_gradient,
            max_gradient=max_gradient,
            object_candidate=edge_density >= self.config.min_edge_density,
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


def _gaussian_kernel1d(sigma: float) -> np.ndarray:
    radius = max(1, int(np.ceil(3 * sigma)))
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-(offsets**2) / (2 * sigma**2))
    return kernel / kernel.sum()


def _to_uint8(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image.copy()
    return np.clip(np.round(image), 0, 255).astype(np.uint8)
