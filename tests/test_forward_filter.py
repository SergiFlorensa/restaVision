from __future__ import annotations

import pytest
from services.decision.sequence import ForwardFilter, MarkovChainModel


def make_model() -> MarkovChainModel:
    return MarkovChainModel(
        states=("ready", "occupied"),
        transition_probabilities={
            "ready": {"ready": 0.90, "occupied": 0.10},
            "occupied": {"ready": 0.05, "occupied": 0.95},
        },
        start_probabilities={"ready": 0.80, "occupied": 0.20},
    )


def test_forward_filter_updates_current_belief_online() -> None:
    filter_ = ForwardFilter(make_model())

    result = filter_.update({"ready": 0.10, "occupied": 0.90})

    assert result.selected_state == "occupied"
    assert result.confidence > 0.5
    assert result.posterior == filter_.belief
    assert sum(result.posterior.values()) == pytest.approx(1.0)


def test_forward_filter_uses_previous_belief_to_resist_single_noisy_observation() -> None:
    filter_ = ForwardFilter(make_model(), initial_belief={"ready": 0.01, "occupied": 0.99})

    result = filter_.update({"ready": 0.65, "occupied": 0.35})

    assert result.selected_state == "occupied"
    assert result.predicted_prior["occupied"] > result.predicted_prior["ready"]


def test_forward_filter_can_reset_to_custom_belief() -> None:
    filter_ = ForwardFilter(make_model())
    filter_.update({"ready": 0.10, "occupied": 0.90})

    filter_.reset({"ready": 1.0, "occupied": 0.0})

    assert filter_.belief["ready"] == pytest.approx(1.0)
    assert filter_.belief["occupied"] == pytest.approx(0.0)


def test_forward_filter_validates_observation_likelihoods() -> None:
    filter_ = ForwardFilter(make_model())

    with pytest.raises(ValueError, match="Missing probabilities"):
        filter_.update({"ready": 1.0})
