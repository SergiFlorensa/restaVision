from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from services.events.models import TableObservation, TableRuntime


class OcclusionStatus(StrEnum):
    VISIBLE = "visible"
    SUSPECTED_OCCLUSION = "suspected_occlusion"
    CAMERA_BLOCKED = "camera_blocked"
    CONFIRMED_EMPTY = "confirmed_empty"


@dataclass(frozen=True, slots=True)
class OcclusionConfig:
    min_empty_observations_before_release: int = 3
    low_confidence_threshold: float = 0.55
    blocked_confidence_threshold: float = 0.15
    blocked_observations_before_alert: int = 3
    sudden_empty_seconds: float = 1.0
    hold_confidence: float = 0.66

    def __post_init__(self) -> None:
        if self.min_empty_observations_before_release < 1:
            raise ValueError("min_empty_observations_before_release must be greater than 0.")
        if not 0 <= self.blocked_confidence_threshold <= self.low_confidence_threshold <= 1:
            raise ValueError("confidence thresholds must be ordered between 0 and 1.")
        if self.blocked_observations_before_alert < 1:
            raise ValueError("blocked_observations_before_alert must be greater than 0.")
        if self.sudden_empty_seconds < 0:
            raise ValueError("sudden_empty_seconds must be non-negative.")
        if not 0 <= self.hold_confidence <= 1:
            raise ValueError("hold_confidence must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class OcclusionDecision:
    status: OcclusionStatus
    original_observation: TableObservation
    effective_observation: TableObservation
    held_previous_count: bool
    empty_observation_count: int
    blocked_observation_count: int
    reason: str


class OcclusionManager:
    def __init__(self, config: OcclusionConfig | None = None) -> None:
        self.config = config or OcclusionConfig()
        self._empty_counts_by_table: dict[str, int] = {}
        self._blocked_counts_by_table: dict[str, int] = {}

    def apply(
        self,
        runtime: TableRuntime,
        observation: TableObservation,
    ) -> OcclusionDecision:
        if observation.people_count < 0:
            raise ValueError("people_count must be non-negative.")
        if not 0 <= observation.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1.")

        if observation.people_count > 0:
            self.reset(observation.table_id)
            return OcclusionDecision(
                status=OcclusionStatus.VISIBLE,
                original_observation=observation,
                effective_observation=observation,
                held_previous_count=False,
                empty_observation_count=0,
                blocked_observation_count=0,
                reason="positive_observation",
            )

        if runtime.active_session_id is None or runtime.last_people_count <= 0:
            self.reset(observation.table_id)
            return OcclusionDecision(
                status=OcclusionStatus.CONFIRMED_EMPTY,
                original_observation=observation,
                effective_observation=observation,
                held_previous_count=False,
                empty_observation_count=0,
                blocked_observation_count=0,
                reason="no_active_occupancy",
            )

        empty_count = self._empty_counts_by_table.get(observation.table_id, 0) + 1
        self._empty_counts_by_table[observation.table_id] = empty_count

        if observation.confidence <= self.config.blocked_confidence_threshold:
            blocked_count = self._blocked_counts_by_table.get(observation.table_id, 0) + 1
        else:
            blocked_count = 0
        self._blocked_counts_by_table[observation.table_id] = blocked_count

        low_confidence = observation.confidence < self.config.low_confidence_threshold
        too_few_empty_samples = empty_count < self.config.min_empty_observations_before_release
        sudden_empty = (
            _seconds_since_update(runtime, observation) <= self.config.sudden_empty_seconds
        )

        if low_confidence or too_few_empty_samples or sudden_empty:
            status = (
                OcclusionStatus.CAMERA_BLOCKED
                if blocked_count >= self.config.blocked_observations_before_alert
                else OcclusionStatus.SUSPECTED_OCCLUSION
            )
            effective = replace(
                observation,
                people_count=runtime.last_people_count,
                confidence=max(observation.confidence, self.config.hold_confidence),
            )
            return OcclusionDecision(
                status=status,
                original_observation=observation,
                effective_observation=effective,
                held_previous_count=True,
                empty_observation_count=empty_count,
                blocked_observation_count=blocked_count,
                reason=_hold_reason(
                    low_confidence=low_confidence,
                    too_few_empty_samples=too_few_empty_samples,
                    sudden_empty=sudden_empty,
                ),
            )

        self.reset(observation.table_id)
        return OcclusionDecision(
            status=OcclusionStatus.CONFIRMED_EMPTY,
            original_observation=observation,
            effective_observation=observation,
            held_previous_count=False,
            empty_observation_count=empty_count,
            blocked_observation_count=blocked_count,
            reason="empty_confirmed",
        )

    def reset(self, table_id: str) -> None:
        self._empty_counts_by_table.pop(table_id, None)
        self._blocked_counts_by_table.pop(table_id, None)


def _seconds_since_update(runtime: TableRuntime, observation: TableObservation) -> float:
    if runtime.updated_at is None:
        return float("inf")
    return max(0.0, (observation.observed_at - runtime.updated_at).total_seconds())


def _hold_reason(
    low_confidence: bool,
    too_few_empty_samples: bool,
    sudden_empty: bool,
) -> str:
    reasons: list[str] = []
    if low_confidence:
        reasons.append("low_confidence")
    if too_few_empty_samples:
        reasons.append("temporal_hysteresis")
    if sudden_empty:
        reasons.append("sudden_empty")
    return "+".join(reasons)
