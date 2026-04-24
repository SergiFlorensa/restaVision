from __future__ import annotations

from dataclasses import dataclass, fields

from services.decision.confidence import normalize_distribution
from services.events.models import TableObservation


@dataclass(frozen=True, slots=True)
class TableObservationLikelihoodConfig:
    empty_ready_likelihood: float = 0.82
    empty_occupied_likelihood: float = 0.10
    empty_finalizing_likelihood: float = 0.04
    empty_pending_cleaning_likelihood: float = 0.04
    occupied_ready_likelihood: float = 0.03
    occupied_occupied_likelihood: float = 0.82
    occupied_finalizing_likelihood: float = 0.10
    occupied_pending_cleaning_likelihood: float = 0.05
    low_confidence_blend: float = 0.45
    low_confidence_threshold: float = 0.55

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name.endswith("_likelihood") and value < 0:
                raise ValueError(f"{field.name} must be non-negative.")
        if not 0 <= self.low_confidence_blend <= 1:
            raise ValueError("low_confidence_blend must be between 0 and 1.")
        if not 0 <= self.low_confidence_threshold <= 1:
            raise ValueError("low_confidence_threshold must be between 0 and 1.")


class TableObservationLikelihoodModel:
    """Maps table observations to state likelihoods for HMM filtering."""

    states = ("ready", "occupied", "finalizing", "pending_cleaning")

    def __init__(self, config: TableObservationLikelihoodConfig | None = None) -> None:
        self.config = config or TableObservationLikelihoodConfig()

    def likelihood(self, observation: TableObservation) -> dict[str, float]:
        if observation.people_count < 0:
            raise ValueError("people_count must be non-negative.")
        if not 0 <= observation.confidence <= 1:
            raise ValueError("observation confidence must be between 0 and 1.")

        if observation.people_count == 0:
            likelihood = {
                "ready": self.config.empty_ready_likelihood,
                "occupied": self.config.empty_occupied_likelihood,
                "finalizing": self.config.empty_finalizing_likelihood,
                "pending_cleaning": self.config.empty_pending_cleaning_likelihood,
            }
        else:
            likelihood = {
                "ready": self.config.occupied_ready_likelihood,
                "occupied": self.config.occupied_occupied_likelihood,
                "finalizing": self.config.occupied_finalizing_likelihood,
                "pending_cleaning": self.config.occupied_pending_cleaning_likelihood,
            }

        normalized = normalize_distribution(likelihood)
        if observation.confidence >= self.config.low_confidence_threshold:
            return normalized

        return self._blend_with_uniform(normalized, self.config.low_confidence_blend)

    def _blend_with_uniform(
        self,
        likelihood: dict[str, float],
        blend: float,
    ) -> dict[str, float]:
        uniform = 1.0 / len(self.states)
        blended = {
            state: (1.0 - blend) * likelihood[state] + blend * uniform for state in self.states
        }
        return normalize_distribution(blended)
