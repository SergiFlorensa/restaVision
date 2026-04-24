from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class MultivariateGaussianProfile:
    feature_names: tuple[str, ...]
    mean: np.ndarray
    covariance: np.ndarray
    precision: np.ndarray
    regularization: float

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    def mahalanobis_squared(self, features: Sequence[float] | Mapping[str, float]) -> float:
        vector = _as_feature_vector(features, self.feature_names)
        delta = vector - self.mean
        return float(delta.T @ self.precision @ delta)

    def feature_z_scores(self, features: Sequence[float] | Mapping[str, float]) -> dict[str, float]:
        vector = _as_feature_vector(features, self.feature_names)
        std = np.sqrt(np.clip(np.diag(self.covariance), self.regularization, None))
        z_scores = (vector - self.mean) / std
        return {
            feature_name: float(z_score)
            for feature_name, z_score in zip(self.feature_names, z_scores, strict=True)
        }


@dataclass(frozen=True, slots=True)
class MultivariateAnomalyConfig:
    max_mahalanobis_squared: float = 9.0
    min_samples: int = 5
    regularization: float = 1e-6

    def __post_init__(self) -> None:
        if self.max_mahalanobis_squared <= 0:
            raise ValueError("max_mahalanobis_squared must be positive.")
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2.")
        if self.regularization <= 0:
            raise ValueError("regularization must be positive.")


@dataclass(frozen=True, slots=True)
class MultivariateAnomalyResult:
    is_anomaly: bool
    mahalanobis_squared: float
    threshold: float
    feature_z_scores: dict[str, float]

    @property
    def severity_score(self) -> float:
        return min(1.0, self.mahalanobis_squared / self.threshold)


class MultivariateGaussianAnomalyDetector:
    """Scores correlated operational features against a Gaussian normal profile."""

    def __init__(
        self,
        profile: MultivariateGaussianProfile,
        config: MultivariateAnomalyConfig | None = None,
    ) -> None:
        self.profile = profile
        self.config = config or MultivariateAnomalyConfig()

    def score(self, features: Sequence[float] | Mapping[str, float]) -> MultivariateAnomalyResult:
        distance_squared = self.profile.mahalanobis_squared(features)
        return MultivariateAnomalyResult(
            is_anomaly=distance_squared >= self.config.max_mahalanobis_squared,
            mahalanobis_squared=distance_squared,
            threshold=self.config.max_mahalanobis_squared,
            feature_z_scores=self.profile.feature_z_scores(features),
        )


def fit_multivariate_gaussian_profile(
    samples: Sequence[Mapping[str, float]] | np.ndarray,
    feature_names: Sequence[str] | None = None,
    *,
    regularization: float = 1e-6,
    min_samples: int = 5,
) -> MultivariateGaussianProfile:
    if regularization <= 0:
        raise ValueError("regularization must be positive.")
    if min_samples < 2:
        raise ValueError("min_samples must be at least 2.")

    resolved_names, matrix = _as_sample_matrix(samples, feature_names)
    if matrix.shape[0] < min_samples:
        raise ValueError("not enough samples to fit a multivariate profile.")
    if matrix.shape[1] == 0:
        raise ValueError("at least one feature is required.")

    mean = matrix.mean(axis=0)
    covariance = np.cov(matrix, rowvar=False, ddof=1)
    covariance = np.atleast_2d(covariance).astype(float)
    regularized_covariance = covariance + np.eye(matrix.shape[1]) * regularization
    precision = np.linalg.pinv(regularized_covariance)

    return MultivariateGaussianProfile(
        feature_names=resolved_names,
        mean=mean,
        covariance=regularized_covariance,
        precision=precision,
        regularization=regularization,
    )


def _as_sample_matrix(
    samples: Sequence[Mapping[str, float]] | np.ndarray,
    feature_names: Sequence[str] | None,
) -> tuple[tuple[str, ...], np.ndarray]:
    if isinstance(samples, np.ndarray):
        matrix = np.asarray(samples, dtype=float)
        if matrix.ndim != 2:
            raise ValueError("sample array must be a 2D matrix.")
        if feature_names is None:
            names = tuple(f"feature_{index}" for index in range(matrix.shape[1]))
        else:
            names = _validate_feature_names(feature_names)
            if len(names) != matrix.shape[1]:
                raise ValueError("feature_names must match the sample feature count.")
        return names, matrix

    rows = list(samples)
    if not rows:
        raise ValueError("samples cannot be empty.")
    names = _validate_feature_names(feature_names or tuple(rows[0].keys()))
    matrix_rows = []
    for row in rows:
        missing = set(names) - set(row)
        if missing:
            raise ValueError(f"sample misses features: {sorted(missing)}")
        matrix_rows.append([float(row[name]) for name in names])
    return names, np.asarray(matrix_rows, dtype=float)


def _as_feature_vector(
    features: Sequence[float] | Mapping[str, float],
    feature_names: tuple[str, ...],
) -> np.ndarray:
    if isinstance(features, Mapping):
        missing = set(feature_names) - set(features)
        if missing:
            raise ValueError(f"features misses keys: {sorted(missing)}")
        return np.asarray([float(features[name]) for name in feature_names], dtype=float)

    vector = np.asarray(features, dtype=float)
    if vector.ndim != 1 or vector.shape[0] != len(feature_names):
        raise ValueError("features must be a 1D vector aligned with the profile.")
    return vector


def _validate_feature_names(feature_names: Sequence[str]) -> tuple[str, ...]:
    names = tuple(feature_names)
    if not names:
        raise ValueError("feature_names cannot be empty.")
    if any(not name for name in names):
        raise ValueError("feature_names cannot contain empty values.")
    if len(set(names)) != len(names):
        raise ValueError("feature_names must be unique.")
    return names
