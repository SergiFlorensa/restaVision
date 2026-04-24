from __future__ import annotations

import numpy as np
import pytest
from services.decision.confidence import (
    ConfidenceGate,
    ConfidenceGateConfig,
    distribution_entropy,
    normalized_entropy_ratio,
    select_temperature_by_nll,
    softmax,
    softmax_dict,
)


def test_softmax_is_stable_and_normalized() -> None:
    probabilities = softmax([1000.0, 1001.0, 999.0])

    assert np.isclose(probabilities.sum(), 1.0)
    assert probabilities.argmax() == 1


def test_softmax_dict_requires_aligned_unique_labels() -> None:
    result = softmax_dict(("ready", "occupied"), (2.0, 0.0))

    assert set(result) == {"ready", "occupied"}
    assert result["ready"] > result["occupied"]

    with pytest.raises(ValueError, match="unique"):
        softmax_dict(("ready", "ready"), (1.0, 0.0))


def test_confidence_gate_accepts_confident_logits() -> None:
    gate = ConfidenceGate(ConfidenceGateConfig(min_confidence=0.80))

    result = gate.evaluate_logits(("ready", "occupied"), (4.0, 0.0))

    assert result.accepted is True
    assert result.label == "ready"
    assert result.reason == "accepted"


def test_confidence_gate_rejects_ambiguous_probabilities() -> None:
    gate = ConfidenceGate(ConfidenceGateConfig(min_confidence=0.70))

    result = gate.evaluate_probabilities({"ready": 0.51, "occupied": 0.49})

    assert result.accepted is False
    assert result.label == "request_review"
    assert result.selected_label == "ready"
    assert result.reason == "confidence_below_threshold"


def test_confidence_gate_can_reject_high_entropy_outputs() -> None:
    gate = ConfidenceGate(ConfidenceGateConfig(min_confidence=0.0, max_entropy_ratio=0.90))

    result = gate.evaluate_probabilities({"ready": 0.50, "occupied": 0.50})

    assert result.accepted is False
    assert result.reason == "entropy_above_threshold"
    assert result.entropy_ratio == pytest.approx(1.0)


def test_entropy_helpers_normalize_distributions() -> None:
    assert distribution_entropy((2.0, 0.0)) == pytest.approx(0.0)
    assert normalized_entropy_ratio((0.5, 0.5)) == pytest.approx(1.0)


def test_select_temperature_by_nll_prefers_calibrated_candidate() -> None:
    logits = np.array([[3.0, 0.0], [0.0, 3.0]])
    targets = np.array([0, 1])

    temperature = select_temperature_by_nll(logits, targets, (0.5, 1.0, 2.0))

    assert temperature == 0.5
