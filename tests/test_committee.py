from __future__ import annotations

import pytest
from services.decision.committee import CommitteePrediction, WeightedPosteriorCommittee
from services.decision.policy import (
    DecisionPolicy,
    DecisionPolicyConfig,
    default_occupancy_loss_matrix,
)


def test_weighted_committee_combines_member_posteriors() -> None:
    committee = WeightedPosteriorCommittee(states=("ready", "occupied"))

    result = committee.combine(
        [
            CommitteePrediction(
                member_id="fast_detector",
                posterior={"ready": 0.8, "occupied": 0.2},
                weight=1.0,
            ),
            CommitteePrediction(
                member_id="stable_detector",
                posterior={"ready": 0.2, "occupied": 0.8},
                weight=3.0,
            ),
        ]
    )

    assert result.member_count == 2
    assert result.total_weight == 4.0
    assert result.posterior["occupied"] == pytest.approx(0.65)
    assert result.posterior["ready"] == pytest.approx(0.35)


def test_weighted_committee_normalizes_each_member_prediction() -> None:
    committee = WeightedPosteriorCommittee(states=("ready", "occupied"))

    result = committee.combine(
        [
            CommitteePrediction(
                member_id="unnormalized",
                posterior={"ready": 8.0, "occupied": 2.0},
            )
        ]
    )

    assert result.posterior == {"ready": 0.8, "occupied": 0.2}


def test_committee_output_can_feed_decision_policy() -> None:
    committee = WeightedPosteriorCommittee(states=("ready", "occupied"))
    policy = DecisionPolicy(
        default_occupancy_loss_matrix(),
        DecisionPolicyConfig(min_confidence=0.60),
    )

    combined = committee.combine(
        [
            CommitteePrediction("geometry", {"ready": 0.75, "occupied": 0.25}),
            CommitteePrediction("temporal", {"ready": 0.55, "occupied": 0.45}),
        ]
    )
    decision = policy.decide(combined.posterior)

    assert decision.action == "mark_occupied"
    assert decision.reason == "minimum_expected_loss"


def test_weighted_committee_validates_inputs() -> None:
    committee = WeightedPosteriorCommittee(states=("ready", "occupied"))

    with pytest.raises(ValueError, match="At least one"):
        committee.combine([])

    with pytest.raises(ValueError, match="Missing posterior states"):
        committee.combine([CommitteePrediction("bad", {"ready": 1.0})])

    with pytest.raises(ValueError, match="positive"):
        committee.combine(
            [CommitteePrediction("bad_weight", {"ready": 1.0, "occupied": 0.0}, weight=0.0)]
        )
