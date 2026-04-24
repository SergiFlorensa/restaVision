from __future__ import annotations

import numpy as np
import pytest
from services.alerts.multivariate import (
    MultivariateAnomalyConfig,
    MultivariateGaussianAnomalyDetector,
    fit_multivariate_gaussian_profile,
)


def test_multivariate_detector_accepts_normal_correlated_pattern() -> None:
    samples = [
        {"duration_min": 40, "people_count": 2, "motion": 0.20},
        {"duration_min": 42, "people_count": 2, "motion": 0.22},
        {"duration_min": 45, "people_count": 3, "motion": 0.25},
        {"duration_min": 47, "people_count": 3, "motion": 0.24},
        {"duration_min": 50, "people_count": 4, "motion": 0.30},
        {"duration_min": 52, "people_count": 4, "motion": 0.31},
    ]
    profile = fit_multivariate_gaussian_profile(samples, min_samples=5)
    detector = MultivariateGaussianAnomalyDetector(
        profile,
        MultivariateAnomalyConfig(max_mahalanobis_squared=9.0),
    )

    result = detector.score({"duration_min": 46, "people_count": 3, "motion": 0.26})

    assert not result.is_anomaly
    assert result.mahalanobis_squared < result.threshold
    assert set(result.feature_z_scores) == {"duration_min", "people_count", "motion"}


def test_multivariate_detector_flags_unusual_feature_combination() -> None:
    samples = np.array(
        [
            [40, 2, 0.20],
            [42, 2, 0.22],
            [45, 3, 0.25],
            [47, 3, 0.24],
            [50, 4, 0.30],
            [52, 4, 0.31],
        ],
        dtype=float,
    )
    profile = fit_multivariate_gaussian_profile(
        samples,
        feature_names=("duration_min", "people_count", "motion"),
        min_samples=5,
    )
    detector = MultivariateGaussianAnomalyDetector(
        profile,
        MultivariateAnomalyConfig(max_mahalanobis_squared=9.0),
    )

    result = detector.score({"duration_min": 100, "people_count": 1, "motion": 0.95})

    assert result.is_anomaly
    assert result.mahalanobis_squared >= result.threshold
    assert result.severity_score == pytest.approx(1.0)


def test_profile_uses_regularization_for_singular_covariance() -> None:
    samples = np.array(
        [
            [1.0, 10.0],
            [2.0, 20.0],
            [3.0, 30.0],
            [4.0, 40.0],
            [5.0, 50.0],
        ]
    )

    profile = fit_multivariate_gaussian_profile(samples, regularization=1e-3, min_samples=5)
    distance = profile.mahalanobis_squared([3.0, 30.0])

    assert np.isfinite(profile.precision).all()
    assert distance == pytest.approx(0.0)


def test_fit_profile_validates_samples_and_feature_names() -> None:
    with pytest.raises(ValueError, match="not enough samples"):
        fit_multivariate_gaussian_profile(np.ones((2, 2)), min_samples=5)

    with pytest.raises(ValueError, match="unique"):
        fit_multivariate_gaussian_profile(
            np.ones((5, 2)),
            feature_names=("x", "x"),
            min_samples=5,
        )

    with pytest.raises(ValueError, match="misses features"):
        fit_multivariate_gaussian_profile(
            [{"x": 1.0, "y": 2.0}, {"x": 2.0}],
            feature_names=("x", "y"),
            min_samples=2,
        )
