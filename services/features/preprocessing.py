from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class PCAProjection:
    mean: np.ndarray
    components: np.ndarray
    explained_variance: np.ndarray
    explained_variance_ratio: np.ndarray
    whiten: bool = False
    epsilon: float = 1e-12

    def transform(self, data: np.ndarray) -> np.ndarray:
        matrix = _as_2d_float_array(data)
        self._validate_feature_count(matrix)

        projected = (matrix - self.mean) @ self.components.T
        if self.whiten:
            projected = projected / np.sqrt(self.explained_variance + self.epsilon)
        return projected

    def inverse_transform(self, projected_data: np.ndarray) -> np.ndarray:
        projected = _as_2d_float_array(projected_data)
        if projected.shape[1] != self.components.shape[0]:
            raise ValueError("projected_data has an unexpected number of components.")

        restored = projected
        if self.whiten:
            restored = restored * np.sqrt(self.explained_variance + self.epsilon)
        return restored @ self.components + self.mean

    @property
    def n_components(self) -> int:
        return int(self.components.shape[0])

    @property
    def n_features(self) -> int:
        return int(self.components.shape[1])

    def _validate_feature_count(self, matrix: np.ndarray) -> None:
        if matrix.shape[1] != self.n_features:
            raise ValueError("data has an unexpected number of features.")


def fit_pca(
    data: np.ndarray,
    n_components: int | None = None,
    explained_variance_threshold: float | None = None,
    whiten: bool = False,
    epsilon: float = 1e-12,
) -> PCAProjection:
    matrix = _as_2d_float_array(data)
    if matrix.shape[0] < 2:
        raise ValueError("PCA requires at least two samples.")
    if n_components is not None and explained_variance_threshold is not None:
        raise ValueError("Use n_components or explained_variance_threshold, not both.")
    if explained_variance_threshold is not None and not 0 < explained_variance_threshold <= 1:
        raise ValueError("explained_variance_threshold must be in the interval (0, 1].")

    mean = matrix.mean(axis=0)
    centered = matrix - mean
    _, singular_values, vectors_t = np.linalg.svd(centered, full_matrices=False)
    explained_variance = (singular_values**2) / (matrix.shape[0] - 1)
    total_variance = float(explained_variance.sum())
    if total_variance > epsilon:
        explained_variance_ratio = explained_variance / total_variance
    else:
        explained_variance_ratio = np.zeros_like(explained_variance)

    max_components = min(matrix.shape)
    selected_components = _select_component_count(
        n_components=n_components,
        explained_variance_threshold=explained_variance_threshold,
        explained_variance_ratio=explained_variance_ratio,
        max_components=max_components,
    )

    return PCAProjection(
        mean=mean,
        components=vectors_t[:selected_components],
        explained_variance=explained_variance[:selected_components],
        explained_variance_ratio=explained_variance_ratio[:selected_components],
        whiten=whiten,
        epsilon=epsilon,
    )


def whiten_features(
    data: np.ndarray,
    n_components: int | None = None,
    epsilon: float = 1e-12,
) -> tuple[np.ndarray, PCAProjection]:
    projection = fit_pca(
        data=data,
        n_components=n_components,
        whiten=True,
        epsilon=epsilon,
    )
    return projection.transform(data), projection


@dataclass(slots=True)
class RunningFeatureStats:
    count: int = 0
    _mean: np.ndarray | None = None
    _m2: np.ndarray | None = None

    def update(self, data: np.ndarray) -> None:
        matrix = _as_2d_float_array(data)
        if self._mean is not None and matrix.shape[1] != self._mean.shape[0]:
            raise ValueError("data has an unexpected number of features.")

        for row in matrix:
            self.count += 1
            if self._mean is None:
                self._mean = np.zeros_like(row, dtype=float)
                self._m2 = np.zeros_like(row, dtype=float)

            delta = row - self._mean
            self._mean = self._mean + (delta / self.count)
            delta_after_update = row - self._mean
            self._m2 = self._m2 + (delta * delta_after_update)

    @property
    def mean(self) -> np.ndarray:
        if self._mean is None:
            raise ValueError("No feature samples have been observed.")
        return self._mean.copy()

    @property
    def variance(self) -> np.ndarray:
        if self._m2 is None or self.count == 0:
            raise ValueError("No feature samples have been observed.")
        return self._m2 / self.count

    @property
    def sample_variance(self) -> np.ndarray:
        if self._m2 is None or self.count < 2:
            raise ValueError("At least two samples are required.")
        return self._m2 / (self.count - 1)


def correlation_matrix(data: np.ndarray, epsilon: float = 1e-12) -> np.ndarray:
    matrix = _as_2d_float_array(data)
    if matrix.shape[0] < 2:
        raise ValueError("Correlation requires at least two samples.")

    centered = matrix - matrix.mean(axis=0)
    std = matrix.std(axis=0, ddof=1)
    non_constant = std > epsilon
    safe_std = np.where(non_constant, std, 1.0)
    normalized = centered / safe_std
    correlation = (normalized.T @ normalized) / (matrix.shape[0] - 1)

    constant_indexes = np.where(~non_constant)[0]
    correlation[constant_indexes, :] = 0.0
    correlation[:, constant_indexes] = 0.0
    for index, is_non_constant in enumerate(non_constant):
        correlation[index, index] = 1.0 if is_non_constant else 0.0

    return correlation


def _select_component_count(
    n_components: int | None,
    explained_variance_threshold: float | None,
    explained_variance_ratio: np.ndarray,
    max_components: int,
) -> int:
    if n_components is not None:
        if n_components < 1 or n_components > max_components:
            raise ValueError("n_components must be between 1 and the PCA rank limit.")
        return n_components

    if explained_variance_threshold is not None:
        cumulative = np.cumsum(explained_variance_ratio)
        if not np.any(cumulative >= explained_variance_threshold):
            return max_components
        return int(np.searchsorted(cumulative, explained_variance_threshold) + 1)

    return max_components


def _as_2d_float_array(data: np.ndarray) -> np.ndarray:
    matrix = np.asarray(data, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("data must be a 2D matrix.")
    if matrix.shape[1] == 0:
        raise ValueError("data must contain at least one feature.")
    return matrix
