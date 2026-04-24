from __future__ import annotations

from datetime import UTC, datetime

import pytest
from services.decision.observation_model import (
    TableObservationLikelihoodConfig,
    TableObservationLikelihoodModel,
)
from services.events.models import TableObservation


def make_observation(people_count: int, confidence: float) -> TableObservation:
    return TableObservation(
        camera_id="cam_01",
        zone_id="zone_01",
        table_id="table_01",
        people_count=people_count,
        confidence=confidence,
        observed_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )


def test_observation_likelihood_maps_empty_observation_to_ready_state() -> None:
    model = TableObservationLikelihoodModel()

    likelihood = model.likelihood(make_observation(people_count=0, confidence=0.90))

    assert likelihood["ready"] > likelihood["occupied"]
    assert sum(likelihood.values()) == pytest.approx(1.0)


def test_observation_likelihood_maps_people_count_to_occupied_state() -> None:
    model = TableObservationLikelihoodModel()

    likelihood = model.likelihood(make_observation(people_count=3, confidence=0.90))

    assert likelihood["occupied"] > likelihood["ready"]
    assert likelihood["occupied"] > likelihood["pending_cleaning"]


def test_observation_likelihood_blends_low_confidence_with_uniform_distribution() -> None:
    model = TableObservationLikelihoodModel(
        TableObservationLikelihoodConfig(
            low_confidence_threshold=0.60,
            low_confidence_blend=0.50,
        )
    )

    high_confidence = model.likelihood(make_observation(people_count=0, confidence=0.90))
    low_confidence = model.likelihood(make_observation(people_count=0, confidence=0.30))

    assert low_confidence["ready"] < high_confidence["ready"]
    assert low_confidence["occupied"] > high_confidence["occupied"]
    assert sum(low_confidence.values()) == pytest.approx(1.0)


def test_observation_likelihood_validates_observation_values() -> None:
    model = TableObservationLikelihoodModel()

    with pytest.raises(ValueError, match="people_count"):
        model.likelihood(make_observation(people_count=-1, confidence=0.90))

    with pytest.raises(ValueError, match="confidence"):
        model.likelihood(make_observation(people_count=1, confidence=1.20))


def test_observation_likelihood_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="low_confidence_blend"):
        TableObservationLikelihoodConfig(low_confidence_blend=2.0)

    with pytest.raises(ValueError, match="empty_ready_likelihood"):
        TableObservationLikelihoodConfig(empty_ready_likelihood=-1.0)
