from __future__ import annotations

import numpy as np
import pytest
from services.vision.drift import (
    VisualDistributionMonitor,
    VisualDriftConfig,
    VisualDriftLevel,
    histogram_l1_distance,
    visual_distribution_signature,
)


def test_visual_distribution_signature_extracts_normalized_histogram() -> None:
    image = np.full((10, 10), 120, dtype=np.uint8)

    signature = visual_distribution_signature(image, VisualDriftConfig(histogram_bins=8))

    assert signature.mean_intensity == 120
    assert signature.std_intensity == 0
    assert np.isclose(sum(signature.histogram), 1.0)
    assert len(signature.histogram) == 8


def test_histogram_l1_distance_is_zero_for_equal_histograms() -> None:
    assert histogram_l1_distance((0.2, 0.8), (0.2, 0.8)) == 0.0


def test_histogram_l1_distance_rejects_different_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        histogram_l1_distance((1.0,), (0.5, 0.5))


def test_visual_distribution_monitor_reports_ok_for_same_signature() -> None:
    config = VisualDriftConfig(histogram_bins=8, warning_score=0.1, drift_score=0.2)
    baseline = visual_distribution_signature(np.full((20, 20), 90, dtype=np.uint8), config)
    monitor = VisualDistributionMonitor(baseline, config)

    report = monitor.compare(baseline)

    assert report.level == VisualDriftLevel.OK
    assert report.score == 0.0


def test_visual_distribution_monitor_reports_drift_for_brightness_shift() -> None:
    config = VisualDriftConfig(histogram_bins=8, warning_score=0.05, drift_score=0.12)
    baseline = visual_distribution_signature(np.full((20, 20), 30, dtype=np.uint8), config)
    current = visual_distribution_signature(np.full((20, 20), 230, dtype=np.uint8), config)
    monitor = VisualDistributionMonitor(baseline, config)

    report = monitor.compare(current)

    assert report.level == VisualDriftLevel.DRIFT
    assert report.brightness_delta > 0.7
