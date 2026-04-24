from __future__ import annotations

import pytest
from services.decision.policy import (
    DecisionPolicy,
    DecisionPolicyConfig,
    default_occupancy_loss_matrix,
)


def test_decision_policy_selects_minimum_expected_loss_action() -> None:
    policy = DecisionPolicy(
        default_occupancy_loss_matrix(),
        DecisionPolicyConfig(min_confidence=0.60),
    )

    result = policy.decide({"ready": 0.95, "occupied": 0.05})

    assert result.action == "mark_ready"
    assert result.rejected is False
    assert result.reason == "minimum_expected_loss"
    assert result.expected_losses["mark_ready"] < result.expected_losses["mark_occupied"]


def test_decision_policy_can_choose_safer_action_over_most_likely_state() -> None:
    policy = DecisionPolicy(
        default_occupancy_loss_matrix(),
        DecisionPolicyConfig(min_confidence=0.60),
    )

    result = policy.decide({"ready": 0.70, "occupied": 0.30})

    assert result.action == "mark_occupied"
    assert result.selected_action == "mark_occupied"
    assert result.rejected is False


def test_decision_policy_rejects_when_confidence_is_low() -> None:
    policy = DecisionPolicy(
        default_occupancy_loss_matrix(),
        DecisionPolicyConfig(min_confidence=0.80, reject_action="request_review"),
    )

    result = policy.decide({"ready": 0.55, "occupied": 0.45})

    assert result.action == "request_review"
    assert result.rejected is True
    assert result.reason == "confidence_below_threshold"


def test_decision_policy_validates_probability_inputs() -> None:
    policy = DecisionPolicy(default_occupancy_loss_matrix())

    with pytest.raises(ValueError, match="Missing posterior"):
        policy.decide({"ready": 1.0})

    with pytest.raises(ValueError, match="non-negative"):
        policy.decide({"ready": 1.2, "occupied": -0.2})
