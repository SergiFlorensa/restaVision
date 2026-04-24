from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class ConfidenceDriftStatus(StrEnum):
    WARMUP = "warmup"
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ConfidenceDriftReport:
    status: ConfidenceDriftStatus
    sample_count: int
    mean_confidence: float
    baseline_mean_confidence: float | None
    drop_from_baseline: float | None
    message: str


@dataclass(frozen=True, slots=True)
class DistributionDriftReport:
    kl_divergence: float
    drift_detected: bool
    threshold: float


class ConfidenceDriftMonitor:
    def __init__(
        self,
        window_size: int = 100,
        min_samples: int = 20,
        warning_confidence: float = 0.50,
        critical_confidence: float = 0.40,
        max_baseline_drop: float = 0.15,
    ) -> None:
        if window_size < 1:
            raise ValueError("window_size must be greater than 0.")
        if min_samples < 1 or min_samples > window_size:
            raise ValueError("min_samples must be between 1 and window_size.")
        if not 0 <= critical_confidence <= warning_confidence <= 1:
            raise ValueError("confidence thresholds must be ordered between 0 and 1.")
        if max_baseline_drop < 0:
            raise ValueError("max_baseline_drop must be non-negative.")

        self.window_size = window_size
        self.min_samples = min_samples
        self.warning_confidence = warning_confidence
        self.critical_confidence = critical_confidence
        self.max_baseline_drop = max_baseline_drop
        self._values: deque[float] = deque(maxlen=window_size)
        self._baseline_mean_confidence: float | None = None

    def observe(self, confidence: float) -> ConfidenceDriftReport:
        if confidence < 0 or confidence > 1:
            raise ValueError("confidence must be between 0 and 1.")
        self._values.append(confidence)
        return self.report()

    def set_baseline(self, confidences: list[float]) -> None:
        if not confidences:
            raise ValueError("confidences must not be empty.")
        if any(confidence < 0 or confidence > 1 for confidence in confidences):
            raise ValueError("all confidences must be between 0 and 1.")
        self._baseline_mean_confidence = float(np.mean(confidences))

    def report(self) -> ConfidenceDriftReport:
        sample_count = len(self._values)
        if sample_count == 0:
            return ConfidenceDriftReport(
                status=ConfidenceDriftStatus.WARMUP,
                sample_count=0,
                mean_confidence=0.0,
                baseline_mean_confidence=self._baseline_mean_confidence,
                drop_from_baseline=None,
                message="Sin muestras de confianza.",
            )

        mean_confidence = float(np.mean(self._values))
        if sample_count < self.min_samples:
            return ConfidenceDriftReport(
                status=ConfidenceDriftStatus.WARMUP,
                sample_count=sample_count,
                mean_confidence=mean_confidence,
                baseline_mean_confidence=self._baseline_mean_confidence,
                drop_from_baseline=None,
                message="Calentando monitor de confianza.",
            )

        drop_from_baseline = None
        baseline_flag = False
        if self._baseline_mean_confidence is not None:
            drop_from_baseline = self._baseline_mean_confidence - mean_confidence
            baseline_flag = drop_from_baseline >= self.max_baseline_drop

        if mean_confidence < self.critical_confidence:
            status = ConfidenceDriftStatus.CRITICAL
            message = "Confianza media crítica: revisar iluminación, lente o calibración."
        elif mean_confidence < self.warning_confidence or baseline_flag:
            status = ConfidenceDriftStatus.WARNING
            message = "Confianza media degradada: conviene recalibrar o revisar la cámara."
        else:
            status = ConfidenceDriftStatus.OK
            message = "Confianza estable."

        return ConfidenceDriftReport(
            status=status,
            sample_count=sample_count,
            mean_confidence=mean_confidence,
            baseline_mean_confidence=self._baseline_mean_confidence,
            drop_from_baseline=drop_from_baseline,
            message=message,
        )

    def reset(self) -> None:
        self._values.clear()


def kl_divergence(
    reference_distribution: np.ndarray,
    current_distribution: np.ndarray,
    epsilon: float = 1e-12,
) -> float:
    reference = _as_probability_distribution(reference_distribution, epsilon)
    current = _as_probability_distribution(current_distribution, epsilon)
    if reference.shape != current.shape:
        raise ValueError("distributions must have the same shape.")
    return float(np.sum(reference * np.log(reference / current)))


def detect_distribution_drift(
    reference_distribution: np.ndarray,
    current_distribution: np.ndarray,
    threshold: float,
    epsilon: float = 1e-12,
) -> DistributionDriftReport:
    if threshold < 0:
        raise ValueError("threshold must be non-negative.")
    divergence = kl_divergence(reference_distribution, current_distribution, epsilon)
    return DistributionDriftReport(
        kl_divergence=divergence,
        drift_detected=divergence >= threshold,
        threshold=threshold,
    )


def _as_probability_distribution(values: np.ndarray, epsilon: float) -> np.ndarray:
    distribution = np.asarray(values, dtype=float)
    if distribution.ndim != 1:
        raise ValueError("distribution must be a 1D vector.")
    if np.any(distribution < 0):
        raise ValueError("distribution values must be non-negative.")
    total = float(distribution.sum())
    if total <= 0:
        raise ValueError("distribution must have positive mass.")
    probability = distribution / total
    return np.clip(probability, epsilon, 1.0)
