from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from services.decision.sequence import MarkovChainModel


def load_markov_chain_model_from_mapping(config: Mapping[str, Any]) -> MarkovChainModel:
    states = _as_string_tuple(config.get("states"), field_name="states")
    transitions = _as_nested_float_mapping(
        config.get("transition_probabilities"),
        field_name="transition_probabilities",
    )
    start_probabilities = config.get("start_probabilities")
    epsilon = float(config.get("epsilon", 1e-12))

    return MarkovChainModel(
        states=states,
        transition_probabilities=transitions,
        start_probabilities=(
            _as_float_mapping(start_probabilities, field_name="start_probabilities")
            if start_probabilities is not None
            else None
        ),
        epsilon=epsilon,
    )


def load_markov_chain_model_from_json(path: str | Path) -> MarkovChainModel:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, Mapping):
        raise ValueError("JSON temporal model config must be an object.")
    return load_markov_chain_model_from_mapping(raw_config)


def load_markov_chain_model(path: str | Path) -> MarkovChainModel:
    config_path = Path(path)
    suffix = config_path.suffix.lower()
    if suffix == ".json":
        return load_markov_chain_model_from_json(config_path)
    if suffix in {".yaml", ".yml"}:
        return _load_markov_chain_model_from_yaml(config_path)
    raise ValueError("Unsupported temporal model config format. Use .json, .yaml or .yml.")


def _load_markov_chain_model_from_yaml(path: Path) -> MarkovChainModel:
    try:
        import yaml  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "YAML temporal model configs require PyYAML. Use JSON or install PyYAML."
        ) from exc

    with path.open("r", encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)
    if not isinstance(raw_config, Mapping):
        raise ValueError("YAML temporal model config must be a mapping.")
    return load_markov_chain_model_from_mapping(raw_config)


def _as_string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ValueError(f"{field_name} must be a list of strings.")
    items = tuple(value)
    if not items:
        raise ValueError(f"{field_name} cannot be empty.")
    if any(not isinstance(item, str) or not item for item in items):
        raise ValueError(f"{field_name} must contain non-empty strings.")
    return items


def _as_float_mapping(value: Any, *, field_name: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object.")
    return {str(key): float(item) for key, item in value.items()}


def _as_nested_float_mapping(value: Any, *, field_name: str) -> dict[str, dict[str, float]]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object.")

    rows: dict[str, dict[str, float]] = {}
    for state, row in value.items():
        rows[str(state)] = _as_float_mapping(
            row,
            field_name=f"{field_name}.{state}",
        )
    return rows
