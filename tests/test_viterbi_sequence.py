from __future__ import annotations

import pytest
from services.decision.sequence import MarkovChainModel, ViterbiDecoder


def test_viterbi_decoder_suppresses_single_frame_state_flicker() -> None:
    model = MarkovChainModel(
        states=("ready", "occupied"),
        transition_probabilities={
            "ready": {"ready": 0.90, "occupied": 0.10},
            "occupied": {"ready": 0.05, "occupied": 0.95},
        },
        start_probabilities={"ready": 0.10, "occupied": 0.90},
    )
    decoder = ViterbiDecoder(model)

    result = decoder.decode(
        [
            {"ready": 0.10, "occupied": 0.90},
            {"ready": 0.70, "occupied": 0.30},
            {"ready": 0.10, "occupied": 0.90},
        ]
    )

    assert result.states == ("occupied", "occupied", "occupied")
    assert result.normalized_log_probability < 0


def test_viterbi_decoder_allows_sustained_state_transition() -> None:
    model = MarkovChainModel(
        states=("ready", "occupied"),
        transition_probabilities={
            "ready": {"ready": 0.90, "occupied": 0.10},
            "occupied": {"ready": 0.20, "occupied": 0.80},
        },
        start_probabilities={"ready": 0.10, "occupied": 0.90},
    )
    decoder = ViterbiDecoder(model)

    result = decoder.decode(
        [
            {"ready": 0.10, "occupied": 0.90},
            {"ready": 0.85, "occupied": 0.15},
            {"ready": 0.90, "occupied": 0.10},
            {"ready": 0.95, "occupied": 0.05},
        ]
    )

    assert result.states[0] == "occupied"
    assert result.states[-2:] == ("ready", "ready")


def test_markov_chain_model_normalizes_transition_rows() -> None:
    model = MarkovChainModel(
        states=("ready", "occupied"),
        transition_probabilities={
            "ready": {"ready": 9.0, "occupied": 1.0},
            "occupied": {"ready": 2.0, "occupied": 8.0},
        },
    )

    assert model.transition_probabilities["ready"]["ready"] == pytest.approx(0.9)
    assert model.transition_probabilities["occupied"]["occupied"] == pytest.approx(0.8)


def test_viterbi_decoder_validates_missing_state_probabilities() -> None:
    model = MarkovChainModel(
        states=("ready", "occupied"),
        transition_probabilities={
            "ready": {"ready": 0.9, "occupied": 0.1},
            "occupied": {"ready": 0.2, "occupied": 0.8},
        },
    )
    decoder = ViterbiDecoder(model)

    with pytest.raises(ValueError, match="Missing probabilities"):
        decoder.decode([{"ready": 1.0}])


def test_markov_chain_model_rejects_invalid_transition_model() -> None:
    with pytest.raises(ValueError, match="Missing transition row"):
        MarkovChainModel(
            states=("ready", "occupied"),
            transition_probabilities={"ready": {"ready": 0.9, "occupied": 0.1}},
        )
