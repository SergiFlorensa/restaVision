from __future__ import annotations

import numpy as np
import pytest
from services.evaluation.metrics import (
    classification_report,
    confusion_matrix,
    evaluate_probability_predictions,
    expected_calibration_error,
    sweep_confidence_thresholds,
)


def test_confusion_matrix_counts_true_and_false_predictions() -> None:
    confusion = confusion_matrix(
        y_true=("ready", "ready", "occupied", "dirty"),
        y_pred=("ready", "occupied", "occupied", "ready"),
        labels=("ready", "occupied", "dirty"),
    )

    assert confusion.matrix.tolist() == [
        [1, 1, 0],
        [0, 1, 0],
        [1, 0, 0],
    ]
    assert confusion.true_positives("ready") == 1
    assert confusion.false_positives("ready") == 1
    assert confusion.false_negatives("ready") == 1


def test_classification_report_exposes_macro_metrics() -> None:
    report = classification_report(
        y_true=("ready", "ready", "occupied", "occupied"),
        y_pred=("ready", "occupied", "occupied", "occupied"),
        labels=("ready", "occupied"),
    )

    assert report.accuracy == pytest.approx(0.75)
    assert report.per_class["ready"].precision == pytest.approx(1.0)
    assert report.per_class["ready"].recall == pytest.approx(0.5)
    assert report.per_class["occupied"].support == 2
    assert 0 < report.macro_f1 < 1


def test_probability_evaluation_reports_nll_brier_and_calibration() -> None:
    labels = ("ready", "occupied")
    y_true = ("ready", "occupied", "occupied")
    probabilities = [
        {"ready": 0.90, "occupied": 0.10},
        {"ready": 0.20, "occupied": 0.80},
        {"ready": 0.60, "occupied": 0.40},
    ]

    report = evaluate_probability_predictions(labels, y_true, probabilities, bins=2)

    assert report.accuracy == pytest.approx(2 / 3)
    assert report.mean_confidence == pytest.approx((0.90 + 0.80 + 0.60) / 3)
    assert report.negative_log_likelihood > 0
    assert report.brier_score > 0
    assert report.calibration.expected_calibration_error > 0
    assert report.classification.per_class["occupied"].recall == pytest.approx(0.5)


def test_expected_calibration_error_aggregates_bins() -> None:
    report = expected_calibration_error(
        confidences=np.array([0.20, 0.80, 0.90]),
        correct=np.array([False, True, True]),
        bins=2,
    )

    assert report.accuracy == pytest.approx(2 / 3)
    assert report.mean_confidence == pytest.approx(0.6333333333)
    assert len(report.bins) == 2
    assert report.bins[0].sample_count == 1
    assert report.bins[1].sample_count == 2


def test_sweep_confidence_thresholds_reports_coverage_tradeoff() -> None:
    points = sweep_confidence_thresholds(
        labels=("ready", "occupied"),
        y_true=("ready", "occupied", "occupied"),
        probability_rows=np.array(
            [
                [0.90, 0.10],
                [0.20, 0.80],
                [0.60, 0.40],
            ]
        ),
        thresholds=(0.0, 0.70, 0.85),
    )

    assert points[0].coverage == pytest.approx(1.0)
    assert points[0].accepted_accuracy == pytest.approx(2 / 3)
    assert points[1].accepted_count == 2
    assert points[1].accepted_accuracy == pytest.approx(1.0)
    assert points[2].accepted_count == 1
    assert points[2].rejected_count == 2


def test_probability_evaluation_validates_label_alignment() -> None:
    with pytest.raises(ValueError, match="misses labels"):
        evaluate_probability_predictions(
            labels=("ready", "occupied"),
            y_true=("ready",),
            probability_rows=[{"ready": 1.0}],
        )
