from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import inf


@dataclass(frozen=True, slots=True)
class LossMatrix:
    states: tuple[str, ...]
    actions: tuple[str, ...]
    losses: dict[str, dict[str, float]]

    def expected_loss(self, action: str, posterior: Mapping[str, float]) -> float:
        if action not in self.actions:
            raise KeyError(f"Unknown action: {action}")
        action_losses = self.losses[action]
        return sum(action_losses[state] * posterior[state] for state in self.states)

    def validate(self) -> None:
        if not self.states:
            raise ValueError("states cannot be empty.")
        if not self.actions:
            raise ValueError("actions cannot be empty.")

        for action in self.actions:
            if action not in self.losses:
                raise ValueError(f"Missing losses for action: {action}")
            missing_states = set(self.states) - set(self.losses[action])
            if missing_states:
                raise ValueError(f"Missing losses for states: {sorted(missing_states)}")
            for state, value in self.losses[action].items():
                if state in self.states and value < 0:
                    raise ValueError("Loss values must be non-negative.")


@dataclass(frozen=True, slots=True)
class DecisionPolicyConfig:
    reject_action: str = "request_review"
    min_confidence: float = 0.70
    min_expected_loss_margin: float = 0.0


@dataclass(frozen=True, slots=True)
class DecisionResult:
    action: str
    selected_action: str
    confidence: float
    rejected: bool
    expected_losses: dict[str, float]
    expected_loss_margin: float
    reason: str


class DecisionPolicy:
    """Bayesian decision rule with an explicit reject option."""

    def __init__(self, loss_matrix: LossMatrix, config: DecisionPolicyConfig | None = None) -> None:
        loss_matrix.validate()
        self.loss_matrix = loss_matrix
        self.config = config or DecisionPolicyConfig()

    def decide(self, posterior: Mapping[str, float]) -> DecisionResult:
        normalized_posterior = self._normalize_posterior(posterior)
        expected_losses = {
            action: self.loss_matrix.expected_loss(action, normalized_posterior)
            for action in self.loss_matrix.actions
        }
        ranked_actions = sorted(expected_losses.items(), key=lambda item: item[1])
        selected_action, selected_loss = ranked_actions[0]
        second_loss = ranked_actions[1][1] if len(ranked_actions) > 1 else inf
        margin = second_loss - selected_loss
        confidence = max(normalized_posterior.values())

        if confidence < self.config.min_confidence:
            return DecisionResult(
                action=self.config.reject_action,
                selected_action=selected_action,
                confidence=confidence,
                rejected=True,
                expected_losses=expected_losses,
                expected_loss_margin=margin,
                reason="confidence_below_threshold",
            )

        if margin < self.config.min_expected_loss_margin:
            return DecisionResult(
                action=self.config.reject_action,
                selected_action=selected_action,
                confidence=confidence,
                rejected=True,
                expected_losses=expected_losses,
                expected_loss_margin=margin,
                reason="expected_loss_margin_below_threshold",
            )

        return DecisionResult(
            action=selected_action,
            selected_action=selected_action,
            confidence=confidence,
            rejected=False,
            expected_losses=expected_losses,
            expected_loss_margin=margin,
            reason="minimum_expected_loss",
        )

    def _normalize_posterior(self, posterior: Mapping[str, float]) -> dict[str, float]:
        missing_states = set(self.loss_matrix.states) - set(posterior)
        if missing_states:
            raise ValueError(f"Missing posterior probabilities: {sorted(missing_states)}")

        cleaned = {state: float(posterior[state]) for state in self.loss_matrix.states}
        if any(value < 0 for value in cleaned.values()):
            raise ValueError("Posterior probabilities must be non-negative.")

        total = sum(cleaned.values())
        if total <= 0:
            raise ValueError("Posterior probabilities must sum to a positive value.")

        return {state: value / total for state, value in cleaned.items()}


def default_occupancy_loss_matrix() -> LossMatrix:
    return LossMatrix(
        states=("ready", "occupied"),
        actions=("mark_ready", "mark_occupied"),
        losses={
            "mark_ready": {
                "ready": 0.0,
                "occupied": 10.0,
            },
            "mark_occupied": {
                "ready": 2.0,
                "occupied": 0.0,
            },
        },
    )
