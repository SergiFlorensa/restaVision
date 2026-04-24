from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommitteePrediction:
    member_id: str
    posterior: Mapping[str, float]
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class CommitteeResult:
    posterior: dict[str, float]
    member_count: int
    total_weight: float


class WeightedPosteriorCommittee:
    """Combines lightweight model posteriors by weighted averaging."""

    def __init__(self, states: tuple[str, ...]) -> None:
        if not states:
            raise ValueError("states cannot be empty.")
        self.states = states

    def combine(self, predictions: list[CommitteePrediction]) -> CommitteeResult:
        if not predictions:
            raise ValueError("At least one prediction is required.")

        accumulator = {state: 0.0 for state in self.states}
        total_weight = 0.0
        for prediction in predictions:
            if prediction.weight <= 0:
                raise ValueError("Committee member weight must be positive.")

            posterior = self._normalize_posterior(prediction.posterior)
            for state, probability in posterior.items():
                accumulator[state] += prediction.weight * probability
            total_weight += prediction.weight

        combined = {state: value / total_weight for state, value in accumulator.items()}
        return CommitteeResult(
            posterior=combined,
            member_count=len(predictions),
            total_weight=total_weight,
        )

    def _normalize_posterior(self, posterior: Mapping[str, float]) -> dict[str, float]:
        missing_states = set(self.states) - set(posterior)
        if missing_states:
            raise ValueError(f"Missing posterior states: {sorted(missing_states)}")

        normalized = {state: float(posterior[state]) for state in self.states}
        if any(value < 0 for value in normalized.values()):
            raise ValueError("Posterior probabilities must be non-negative.")

        total = sum(normalized.values())
        if total <= 0:
            raise ValueError("Posterior probabilities must sum to a positive value.")

        return {state: value / total for state, value in normalized.items()}
