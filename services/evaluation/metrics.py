from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from services.decision.confidence import normalize_distribution


@dataclass(frozen=True, slots=True)
class ConfusionMatrix:
    labels: tuple[str, ...]
    matrix: np.ndarray

    def true_positives(self, label: str) -> int:
        index = self._label_index(label)
        return int(self.matrix[index, index])

    def false_positives(self, label: str) -> int:
        index = self._label_index(label)
        return int(self.matrix[:, index].sum() - self.matrix[index, index])

    def false_negatives(self, label: str) -> int:
        index = self._label_index(label)
        return int(self.matrix[index, :].sum() - self.matrix[index, index])

    def support(self, label: str) -> int:
        index = self._label_index(label)
        return int(self.matrix[index, :].sum())

    def _label_index(self, label: str) -> int:
        if label not in self.labels:
            raise KeyError(f"Unknown label: {label}")
        return self.labels.index(label)


@dataclass(frozen=True, slots=True)
class ClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True, slots=True)
class ClassificationReport:
    labels: tuple[str, ...]
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    per_class: dict[str, ClassMetrics]
    confusion: ConfusionMatrix


@dataclass(frozen=True, slots=True)
class CalibrationBin:
    lower: float
    upper: float
    sample_count: int
    accuracy: float
    mean_confidence: float
    gap: float


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    expected_calibration_error: float
    mean_confidence: float
    accuracy: float
    bins: tuple[CalibrationBin, ...]


@dataclass(frozen=True, slots=True)
class ProbabilityEvaluationReport:
    labels: tuple[str, ...]
    accuracy: float
    mean_confidence: float
    negative_log_likelihood: float
    brier_score: float
    calibration: CalibrationReport
    classification: ClassificationReport


@dataclass(frozen=True, slots=True)
class ThresholdSweepPoint:
    threshold: float
    coverage: float
    accepted_count: int
    rejected_count: int
    accepted_accuracy: float
    overall_accuracy_with_rejects: float


def confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> ConfusionMatrix:
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have the same length.")
    if len(y_true) == 0:
        raise ValueError("at least one sample is required.")

    resolved_labels = _resolve_labels(y_true, y_pred, labels)
    label_to_index = {label: index for index, label in enumerate(resolved_labels)}
    matrix = np.zeros((len(resolved_labels), len(resolved_labels)), dtype=np.int64)

    for true_label, pred_label in zip(y_true, y_pred, strict=True):
        if true_label not in label_to_index:
            raise ValueError(f"Unknown true label: {true_label}")
        if pred_label not in label_to_index:
            raise ValueError(f"Unknown predicted label: {pred_label}")
        matrix[label_to_index[true_label], label_to_index[pred_label]] += 1

    return ConfusionMatrix(labels=resolved_labels, matrix=matrix)


def classification_report(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None = None,
) -> ClassificationReport:
    confusion = confusion_matrix(y_true, y_pred, labels)
    per_class: dict[str, ClassMetrics] = {}

    for label in confusion.labels:
        true_positives = confusion.true_positives(label)
        false_positives = confusion.false_positives(label)
        false_negatives = confusion.false_negatives(label)
        precision = _safe_divide(true_positives, true_positives + false_positives)
        recall = _safe_divide(true_positives, true_positives + false_negatives)
        f1 = _safe_divide(2 * precision * recall, precision + recall)
        per_class[label] = ClassMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            support=confusion.support(label),
        )

    total = int(confusion.matrix.sum())
    accuracy = float(np.trace(confusion.matrix) / total)
    return ClassificationReport(
        labels=confusion.labels,
        accuracy=accuracy,
        macro_precision=float(np.mean([metrics.precision for metrics in per_class.values()])),
        macro_recall=float(np.mean([metrics.recall for metrics in per_class.values()])),
        macro_f1=float(np.mean([metrics.f1 for metrics in per_class.values()])),
        per_class=per_class,
        confusion=confusion,
    )


def evaluate_probability_predictions(
    labels: Sequence[str],
    y_true: Sequence[str],
    probability_rows: Sequence[Mapping[str, float]] | np.ndarray,
    *,
    bins: int = 10,
) -> ProbabilityEvaluationReport:
    labels_tuple = _validate_labels(labels)
    probabilities = _probability_matrix(labels_tuple, probability_rows)
    if probabilities.shape[0] != len(y_true):
        raise ValueError("probability rows must be aligned with y_true.")

    true_indices = _target_indices(labels_tuple, y_true)
    predicted_indices = np.argmax(probabilities, axis=1)
    confidences = np.max(probabilities, axis=1)
    correct = predicted_indices == true_indices
    y_pred = tuple(labels_tuple[index] for index in predicted_indices)

    selected_probabilities = np.clip(
        probabilities[np.arange(len(true_indices)), true_indices],
        1e-12,
        1.0,
    )
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(len(true_indices)), true_indices] = 1.0

    calibration = expected_calibration_error(confidences, correct, bins=bins)
    return ProbabilityEvaluationReport(
        labels=labels_tuple,
        accuracy=float(np.mean(correct)),
        mean_confidence=float(np.mean(confidences)),
        negative_log_likelihood=float(-np.mean(np.log(selected_probabilities))),
        brier_score=float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        calibration=calibration,
        classification=classification_report(y_true, y_pred, labels_tuple),
    )


def expected_calibration_error(
    confidences: Sequence[float] | np.ndarray,
    correct: Sequence[bool] | np.ndarray,
    *,
    bins: int = 10,
) -> CalibrationReport:
    if bins <= 0:
        raise ValueError("bins must be positive.")

    confidence_values = np.asarray(confidences, dtype=np.float64)
    correct_values = np.asarray(correct, dtype=bool)
    if confidence_values.ndim != 1 or correct_values.ndim != 1:
        raise ValueError("confidences and correct must be 1D sequences.")
    if len(confidence_values) == 0 or len(confidence_values) != len(correct_values):
        raise ValueError("confidences and correct must be non-empty and aligned.")
    if np.any(confidence_values < 0) or np.any(confidence_values > 1):
        raise ValueError("confidences must be between 0 and 1.")

    calibration_bins: list[CalibrationBin] = []
    ece = 0.0
    total = len(confidence_values)
    for bin_index in range(bins):
        lower = bin_index / bins
        upper = (bin_index + 1) / bins
        if bin_index == bins - 1:
            mask = (confidence_values >= lower) & (confidence_values <= upper)
        else:
            mask = (confidence_values >= lower) & (confidence_values < upper)

        sample_count = int(mask.sum())
        if sample_count == 0:
            calibration_bins.append(
                CalibrationBin(
                    lower=lower,
                    upper=upper,
                    sample_count=0,
                    accuracy=0.0,
                    mean_confidence=0.0,
                    gap=0.0,
                )
            )
            continue

        bin_accuracy = float(np.mean(correct_values[mask]))
        bin_confidence = float(np.mean(confidence_values[mask]))
        gap = abs(bin_accuracy - bin_confidence)
        ece += (sample_count / total) * gap
        calibration_bins.append(
            CalibrationBin(
                lower=lower,
                upper=upper,
                sample_count=sample_count,
                accuracy=bin_accuracy,
                mean_confidence=bin_confidence,
                gap=gap,
            )
        )

    return CalibrationReport(
        expected_calibration_error=float(ece),
        mean_confidence=float(np.mean(confidence_values)),
        accuracy=float(np.mean(correct_values)),
        bins=tuple(calibration_bins),
    )


def sweep_confidence_thresholds(
    labels: Sequence[str],
    y_true: Sequence[str],
    probability_rows: Sequence[Mapping[str, float]] | np.ndarray,
    thresholds: Sequence[float],
) -> tuple[ThresholdSweepPoint, ...]:
    if not thresholds:
        raise ValueError("thresholds cannot be empty.")
    if any(threshold < 0 or threshold > 1 for threshold in thresholds):
        raise ValueError("thresholds must be between 0 and 1.")

    labels_tuple = _validate_labels(labels)
    probabilities = _probability_matrix(labels_tuple, probability_rows)
    if probabilities.shape[0] != len(y_true):
        raise ValueError("probability rows must be aligned with y_true.")

    true_indices = _target_indices(labels_tuple, y_true)
    predicted_indices = np.argmax(probabilities, axis=1)
    confidences = np.max(probabilities, axis=1)
    correct = predicted_indices == true_indices

    points: list[ThresholdSweepPoint] = []
    total = len(true_indices)
    for threshold in thresholds:
        accepted = confidences >= threshold
        accepted_count = int(accepted.sum())
        rejected_count = total - accepted_count
        accepted_accuracy = float(np.mean(correct[accepted])) if accepted_count > 0 else 0.0
        points.append(
            ThresholdSweepPoint(
                threshold=float(threshold),
                coverage=accepted_count / total,
                accepted_count=accepted_count,
                rejected_count=rejected_count,
                accepted_accuracy=accepted_accuracy,
                overall_accuracy_with_rejects=float(correct[accepted].sum() / total),
            )
        )

    return tuple(points)


def _resolve_labels(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    labels: Sequence[str] | None,
) -> tuple[str, ...]:
    if labels is not None:
        labels_tuple = _validate_labels(labels)
        unknown = (set(y_true) | set(y_pred)) - set(labels_tuple)
        if unknown:
            raise ValueError(f"labels does not include observed classes: {sorted(unknown)}")
        return labels_tuple

    return tuple(sorted(set(y_true) | set(y_pred)))


def _validate_labels(labels: Sequence[str]) -> tuple[str, ...]:
    labels_tuple = tuple(labels)
    if not labels_tuple:
        raise ValueError("labels cannot be empty.")
    if any(not label for label in labels_tuple):
        raise ValueError("labels cannot contain empty values.")
    if len(set(labels_tuple)) != len(labels_tuple):
        raise ValueError("labels must be unique.")
    return labels_tuple


def _probability_matrix(
    labels: tuple[str, ...],
    probability_rows: Sequence[Mapping[str, float]] | np.ndarray,
) -> np.ndarray:
    if isinstance(probability_rows, np.ndarray):
        matrix = np.asarray(probability_rows, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != len(labels):
            raise ValueError("probability array must have shape (n_samples, n_labels).")
        if np.any(matrix < 0):
            raise ValueError("probabilities must be non-negative.")
        totals = matrix.sum(axis=1)
        if np.any(totals <= 0):
            raise ValueError("each probability row must have positive mass.")
        return matrix / totals[:, None]

    rows = []
    for row in probability_rows:
        normalized = normalize_distribution(row)
        missing = set(labels) - set(normalized)
        if missing:
            raise ValueError(f"probability row misses labels: {sorted(missing)}")
        rows.append([normalized[label] for label in labels])

    if not rows:
        raise ValueError("probability_rows cannot be empty.")
    return np.asarray(rows, dtype=np.float64)


def _target_indices(labels: tuple[str, ...], y_true: Sequence[str]) -> np.ndarray:
    label_to_index = {label: index for index, label in enumerate(labels)}
    indices = []
    for label in y_true:
        if label not in label_to_index:
            raise ValueError(f"Unknown target label: {label}")
        indices.append(label_to_index[label])
    return np.asarray(indices, dtype=np.int64)


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)
