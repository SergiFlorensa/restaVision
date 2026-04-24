from __future__ import annotations

import numpy as np
from services.monitoring.health import (
    ConfidenceDriftMonitor,
    ConfidenceDriftStatus,
    detect_distribution_drift,
    kl_divergence,
)


def test_confidence_monitor_reports_warning_when_confidence_drops_from_baseline() -> None:
    monitor = ConfidenceDriftMonitor(
        window_size=5,
        min_samples=3,
        warning_confidence=0.50,
        critical_confidence=0.40,
        max_baseline_drop=0.15,
    )
    monitor.set_baseline([0.90, 0.88, 0.92])

    monitor.observe(0.70)
    monitor.observe(0.71)
    report = monitor.observe(0.69)

    assert report.status == ConfidenceDriftStatus.WARNING
    assert report.drop_from_baseline is not None
    assert report.drop_from_baseline > 0.15


def test_confidence_monitor_reports_critical_for_low_mean_confidence() -> None:
    monitor = ConfidenceDriftMonitor(window_size=3, min_samples=3)

    monitor.observe(0.30)
    monitor.observe(0.35)
    report = monitor.observe(0.34)

    assert report.status == ConfidenceDriftStatus.CRITICAL


def test_kl_divergence_is_zero_for_equal_distributions() -> None:
    divergence = kl_divergence(np.array([1, 2, 1]), np.array([1, 2, 1]))

    assert divergence == 0.0


def test_detect_distribution_drift_uses_kl_threshold() -> None:
    report = detect_distribution_drift(
        reference_distribution=np.array([90, 10]),
        current_distribution=np.array([10, 90]),
        threshold=1.0,
    )

    assert report.drift_detected
    assert report.kl_divergence >= 1.0
