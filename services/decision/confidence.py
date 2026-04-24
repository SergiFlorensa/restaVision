from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from math import log

import numpy as np


@dataclass(frozen=True, slots=True)
class ConfidenceGateConfig:
    min_confidence: float = 0.85
    max_entropy_ratio: float | None = None
    reject_label: str = "request_review"

    def __post_init__(self) -> None:
        if not 0 <= self.min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1.")
        if self.max_entropy_ratio is not None and not 0 <= self.max_entropy_ratio <= 1:
            raise ValueError("max_entropy_ratio must be between 0 and 1.")
        if not self.reject_label:
            raise ValueError("reject_label cannot be empty.")


@dataclass(frozen=True, slots=True)
class ConfidenceGateResult:
    label: str
    selected_label: str
    confidence: float
    entropy: float
    entropy_ratio: float
    accepted: bool
    probabilities: dict[str, float]
    reason: str


class ConfidenceGate:
    """Rejects low-quality model outputs before they become operational events."""

    def __init__(self, config: ConfidenceGateConfig | None = None) -> None:
        self.config = config or ConfidenceGateConfig()

    def evaluate_logits(
        self,
        labels: Sequence[str],
        logits: Sequence[float] | np.ndarray,
        *,
        temperature: float = 1.0,
    ) -> ConfidenceGateResult:
        probabilities = softmax_dict(labels, logits, temperature=temperature)
        return self.evaluate_probabilities(probabilities)

    def evaluate_probabilities(self, probabilities: Mapping[str, float]) -> ConfidenceGateResult:
        normalized = normalize_distribution(probabilities)
        selected_label, confidence = max(normalized.items(), key=lambda item: item[1])
        entropy = distribution_entropy(normalized.values())
        entropy_ratio = normalized_entropy_ratio(normalized.values())

        if confidence < self.config.min_confidence:
            return ConfidenceGateResult(
                label=self.config.reject_label,
                selected_label=selected_label,
                confidence=confidence,
                entropy=entropy,
                entropy_ratio=entropy_ratio,
                accepted=False,
                probabilities=normalized,
                reason="confidence_below_threshold",
            )

        if (
            self.config.max_entropy_ratio is not None
            and entropy_ratio > self.config.max_entropy_ratio
        ):
            return ConfidenceGateResult(
                label=self.config.reject_label,
                selected_label=selected_label,
                confidence=confidence,
                entropy=entropy,
                entropy_ratio=entropy_ratio,
                accepted=False,
                probabilities=normalized,
                reason="entropy_above_threshold",
            )

        return ConfidenceGateResult(
            label=selected_label,
            selected_label=selected_label,
            confidence=confidence,
            entropy=entropy,
            entropy_ratio=entropy_ratio,
            accepted=True,
            probabilities=normalized,
            reason="accepted",
        )


def softmax(logits: Sequence[float] | np.ndarray, *, temperature: float = 1.0) -> np.ndarray:
    if temperature <= 0:
        raise ValueError("temperature must be positive.")

    values = np.asarray(logits, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("logits must be a non-empty 1D sequence.")
    if not np.all(np.isfinite(values)):
        raise ValueError("logits must contain finite values.")

    scaled = values / temperature
    shifted = scaled - np.max(scaled)
    exp_values = np.exp(shifted)
    total = float(exp_values.sum())
    if total <= 0 or not np.isfinite(total):
        raise ValueError("softmax normalization failed.")
    return exp_values / total


def softmax_dict(
    labels: Sequence[str],
    logits: Sequence[float] | np.ndarray,
    *,
    temperature: float = 1.0,
) -> dict[str, float]:
    if len(labels) == 0:
        raise ValueError("labels cannot be empty.")
    if len(set(labels)) != len(labels):
        raise ValueError("labels must be unique.")

    probabilities = softmax(logits, temperature=temperature)
    if len(labels) != len(probabilities):
        raise ValueError("labels and logits must have the same length.")
    return dict(zip(labels, (float(value) for value in probabilities), strict=True))


def normalize_distribution(probabilities: Mapping[str, float]) -> dict[str, float]:
    if not probabilities:
        raise ValueError("probabilities cannot be empty.")

    cleaned = {label: float(value) for label, value in probabilities.items()}
    if any(not label for label in cleaned):
        raise ValueError("probability labels cannot be empty.")
    if any(not np.isfinite(value) for value in cleaned.values()):
        raise ValueError("probabilities must contain finite values.")
    if any(value < 0 for value in cleaned.values()):
        raise ValueError("probabilities must be non-negative.")

    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("probabilities must sum to a positive value.")
    return {label: value / total for label, value in cleaned.items()}


def distribution_entropy(probabilities: Iterable[float]) -> float:
    values = np.asarray(tuple(probabilities), dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("probabilities must be a non-empty 1D sequence.")
    if np.any(values < 0):
        raise ValueError("probabilities must be non-negative.")

    total = float(values.sum())
    if total <= 0:
        raise ValueError("probabilities must sum to a positive value.")
    normalized = values / total
    positive = normalized[normalized > 0]
    return float(-np.sum(positive * np.log(positive)))


def normalized_entropy_ratio(probabilities: Iterable[float]) -> float:
    values = tuple(probabilities)
    if len(values) <= 1:
        return 0.0
    return distribution_entropy(values) / log(len(values))


def select_temperature_by_nll(
    logits_batch: Sequence[Sequence[float]] | np.ndarray,
    target_indices: Sequence[int] | np.ndarray,
    candidate_temperatures: Sequence[float],
) -> float:
    logits_array = np.asarray(logits_batch, dtype=np.float64)
    targets = np.asarray(target_indices, dtype=np.int64)

    if logits_array.ndim != 2 or logits_array.shape[0] == 0 or logits_array.shape[1] == 0:
        raise ValueError("logits_batch must be a non-empty 2D array.")
    if targets.ndim != 1 or len(targets) != logits_array.shape[0]:
        raise ValueError("target_indices must be a 1D array aligned with logits_batch.")
    if np.any(targets < 0) or np.any(targets >= logits_array.shape[1]):
        raise ValueError("target_indices contains an out-of-range class index.")
    if not candidate_temperatures:
        raise ValueError("candidate_temperatures cannot be empty.")

    best_temperature = float(candidate_temperatures[0])
    best_loss = float("inf")
    for temperature in candidate_temperatures:
        temperature = float(temperature)
        if temperature <= 0:
            raise ValueError("candidate temperatures must be positive.")
        probabilities = _softmax_2d(logits_array, temperature)
        selected = probabilities[np.arange(len(targets)), targets]
        loss = float(-np.mean(np.log(np.clip(selected, 1e-12, 1.0))))
        if loss < best_loss:
            best_loss = loss
            best_temperature = temperature

    return best_temperature


def _softmax_2d(logits: np.ndarray, temperature: float) -> np.ndarray:
    scaled = logits / temperature
    shifted = scaled - np.max(scaled, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values, axis=1, keepdims=True)
