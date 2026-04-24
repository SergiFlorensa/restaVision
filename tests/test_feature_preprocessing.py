from __future__ import annotations

import numpy as np
import pytest
from services.features.preprocessing import (
    RunningFeatureStats,
    correlation_matrix,
    fit_pca,
    whiten_features,
)


def test_fit_pca_reduces_features_and_reports_explained_variance() -> None:
    data = np.array(
        [
            [1.0, 1.0, 0.0],
            [2.0, 2.0, 0.0],
            [3.0, 3.0, 0.0],
            [4.0, 4.0, 0.0],
        ]
    )

    projection = fit_pca(data, n_components=1)
    transformed = projection.transform(data)
    restored = projection.inverse_transform(transformed)

    assert transformed.shape == (4, 1)
    assert projection.explained_variance_ratio[0] > 0.99
    assert np.allclose(restored[:, :2], data[:, :2])


def test_fit_pca_can_select_component_count_by_variance_threshold() -> None:
    data = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.1],
            [2.0, 2.0, 0.2],
            [3.0, 3.0, 0.3],
            [4.0, 4.0, 0.4],
        ]
    )

    projection = fit_pca(data, explained_variance_threshold=0.95)

    assert projection.n_components == 1


def test_whiten_features_returns_unit_covariance_in_pca_space() -> None:
    data = np.array(
        [
            [1.0, 2.0],
            [2.0, 4.0],
            [3.0, 6.0],
            [4.0, 8.0],
            [5.0, 10.0],
        ]
    )

    whitened, projection = whiten_features(data, n_components=1)
    covariance = np.cov(whitened, rowvar=False)

    assert projection.whiten is True
    assert whitened.shape == (5, 1)
    assert np.allclose(covariance, 1.0)


def test_running_feature_stats_matches_numpy_batch_statistics() -> None:
    data = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0]])
    stats = RunningFeatureStats()

    stats.update(data[:2])
    stats.update(data[2:])

    assert stats.count == 4
    assert np.allclose(stats.mean, data.mean(axis=0))
    assert np.allclose(stats.variance, data.var(axis=0))
    assert np.allclose(stats.sample_variance, data.var(axis=0, ddof=1))


def test_correlation_matrix_handles_constant_features_without_nan() -> None:
    data = np.array(
        [
            [1.0, 10.0, 7.0],
            [2.0, 20.0, 7.0],
            [3.0, 30.0, 7.0],
            [4.0, 40.0, 7.0],
        ]
    )

    correlation = correlation_matrix(data)

    assert np.isfinite(correlation).all()
    assert np.allclose(correlation[:2, :2], np.ones((2, 2)))
    assert np.allclose(correlation[2, :], np.zeros(3))
    assert np.allclose(correlation[:, 2], np.zeros(3))


def test_pca_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="at least two samples"):
        fit_pca(np.array([[1.0, 2.0]]))

    with pytest.raises(ValueError, match="Use n_components"):
        fit_pca(np.ones((3, 2)), n_components=1, explained_variance_threshold=0.9)
