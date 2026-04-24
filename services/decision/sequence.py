from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log

import numpy as np

from services.decision.confidence import normalize_distribution


@dataclass(frozen=True, slots=True)
class MarkovChainModel:
    states: tuple[str, ...]
    transition_probabilities: dict[str, dict[str, float]]
    start_probabilities: dict[str, float] | None = None
    epsilon: float = 1e-12

    def __post_init__(self) -> None:
        if not self.states:
            raise ValueError("states cannot be empty.")
        if len(set(self.states)) != len(self.states):
            raise ValueError("states must be unique.")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive.")

        normalized_transitions: dict[str, dict[str, float]] = {}
        for state in self.states:
            if state not in self.transition_probabilities:
                raise ValueError(f"Missing transition row for state: {state}")
            normalized_transitions[state] = _normalize_state_distribution(
                self.transition_probabilities[state],
                self.states,
            )

        object.__setattr__(self, "transition_probabilities", normalized_transitions)

        if self.start_probabilities is not None:
            object.__setattr__(
                self,
                "start_probabilities",
                _normalize_state_distribution(self.start_probabilities, self.states),
            )


@dataclass(frozen=True, slots=True)
class ViterbiResult:
    states: tuple[str, ...]
    log_probability: float
    normalized_log_probability: float
    step_log_probabilities: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ForwardFilterResult:
    posterior: dict[str, float]
    predicted_prior: dict[str, float]
    observation_likelihood: dict[str, float]
    selected_state: str
    confidence: float


class ViterbiDecoder:
    """MAP inference for a discrete Markov chain with observed state posteriors."""

    def __init__(self, model: MarkovChainModel) -> None:
        self.model = model

    def decode(self, observations: Sequence[Mapping[str, float]]) -> ViterbiResult:
        if not observations:
            raise ValueError("observations cannot be empty.")

        emissions = [
            _normalize_state_distribution(observation, self.model.states)
            for observation in observations
        ]
        state_count = len(self.model.states)
        time_count = len(emissions)
        scores = np.full((time_count, state_count), -np.inf, dtype=float)
        backpointers = np.zeros((time_count, state_count), dtype=np.int64)
        start = self._start_probabilities()

        for state_index, state in enumerate(self.model.states):
            scores[0, state_index] = self._safe_log(start[state]) + self._safe_log(
                emissions[0][state]
            )

        for time_index in range(1, time_count):
            for state_index, state in enumerate(self.model.states):
                candidates = []
                for prev_index, prev_state in enumerate(self.model.states):
                    transition = self.model.transition_probabilities[prev_state][state]
                    previous_score = scores[time_index - 1, prev_index]
                    candidates.append(previous_score + self._safe_log(transition))

                best_prev_index = int(np.argmax(candidates))
                scores[time_index, state_index] = candidates[best_prev_index] + self._safe_log(
                    emissions[time_index][state]
                )
                backpointers[time_index, state_index] = best_prev_index

        best_last_index = int(np.argmax(scores[-1]))
        best_score = float(scores[-1, best_last_index])
        state_indexes = [best_last_index]
        for time_index in range(time_count - 1, 0, -1):
            state_indexes.append(int(backpointers[time_index, state_indexes[-1]]))
        state_indexes.reverse()

        decoded_states = tuple(self.model.states[index] for index in state_indexes)
        return ViterbiResult(
            states=decoded_states,
            log_probability=best_score,
            normalized_log_probability=best_score / time_count,
            step_log_probabilities=tuple(
                float(scores[time_index, state_index])
                for time_index, state_index in enumerate(state_indexes)
            ),
        )

    def _start_probabilities(self) -> dict[str, float]:
        if self.model.start_probabilities is not None:
            return self.model.start_probabilities
        uniform = 1.0 / len(self.model.states)
        return {state: uniform for state in self.model.states}

    def _safe_log(self, probability: float) -> float:
        return log(max(probability, self.model.epsilon))


class ForwardFilter:
    """Online HMM filtering for the current state distribution."""

    def __init__(
        self,
        model: MarkovChainModel,
        initial_belief: Mapping[str, float] | None = None,
    ) -> None:
        self.model = model
        self._belief = (
            _normalize_state_distribution(initial_belief, model.states)
            if initial_belief is not None
            else self._start_probabilities()
        )

    @property
    def belief(self) -> dict[str, float]:
        return dict(self._belief)

    def reset(self, belief: Mapping[str, float] | None = None) -> None:
        self._belief = (
            _normalize_state_distribution(belief, self.model.states)
            if belief is not None
            else self._start_probabilities()
        )

    def update(self, observation_likelihood: Mapping[str, float]) -> ForwardFilterResult:
        likelihood = _normalize_state_distribution(observation_likelihood, self.model.states)
        predicted_prior = self._predict_prior()
        unnormalized = {
            state: predicted_prior[state] * likelihood[state] for state in self.model.states
        }
        posterior = normalize_distribution(unnormalized)
        selected_state, confidence = max(posterior.items(), key=lambda item: item[1])
        self._belief = posterior
        return ForwardFilterResult(
            posterior=posterior,
            predicted_prior=predicted_prior,
            observation_likelihood=likelihood,
            selected_state=selected_state,
            confidence=confidence,
        )

    def _predict_prior(self) -> dict[str, float]:
        predicted = {}
        for state in self.model.states:
            predicted[state] = sum(
                self._belief[previous_state]
                * self.model.transition_probabilities[previous_state][state]
                for previous_state in self.model.states
            )
        return normalize_distribution(predicted)

    def _start_probabilities(self) -> dict[str, float]:
        if self.model.start_probabilities is not None:
            return dict(self.model.start_probabilities)
        uniform = 1.0 / len(self.model.states)
        return {state: uniform for state in self.model.states}


def _normalize_state_distribution(
    probabilities: Mapping[str, float],
    states: tuple[str, ...],
) -> dict[str, float]:
    missing_states = set(states) - set(probabilities)
    if missing_states:
        raise ValueError(f"Missing probabilities for states: {sorted(missing_states)}")
    return normalize_distribution({state: probabilities[state] for state in states})
