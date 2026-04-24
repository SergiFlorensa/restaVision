from __future__ import annotations

import json

import pytest
from services.decision.sequence_config import (
    load_markov_chain_model,
    load_markov_chain_model_from_json,
    load_markov_chain_model_from_mapping,
)


def make_config() -> dict[str, object]:
    return {
        "states": ["ready", "occupied"],
        "start_probabilities": {"ready": 0.8, "occupied": 0.2},
        "transition_probabilities": {
            "ready": {"ready": 9, "occupied": 1},
            "occupied": {"ready": 2, "occupied": 8},
        },
    }


def test_load_markov_chain_model_from_mapping_normalizes_probabilities() -> None:
    model = load_markov_chain_model_from_mapping(make_config())

    assert model.states == ("ready", "occupied")
    assert model.start_probabilities == {"ready": 0.8, "occupied": 0.2}
    assert model.transition_probabilities["ready"]["ready"] == pytest.approx(0.9)
    assert model.transition_probabilities["occupied"]["occupied"] == pytest.approx(0.8)


def test_load_markov_chain_model_from_json_file(tmp_path) -> None:
    config_path = tmp_path / "temporal_model.json"
    config_path.write_text(json.dumps(make_config()), encoding="utf-8")

    model = load_markov_chain_model_from_json(config_path)
    model_from_auto_loader = load_markov_chain_model(config_path)

    assert model.transition_probabilities == model_from_auto_loader.transition_probabilities


def test_load_markov_chain_model_rejects_unsupported_extension(tmp_path) -> None:
    config_path = tmp_path / "temporal_model.toml"
    config_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported"):
        load_markov_chain_model(config_path)


def test_load_markov_chain_model_validates_required_fields() -> None:
    with pytest.raises(ValueError, match="states"):
        load_markov_chain_model_from_mapping({"transition_probabilities": {}})

    with pytest.raises(ValueError, match="transition_probabilities"):
        load_markov_chain_model_from_mapping({"states": ["ready"]})


def test_load_markov_chain_model_yaml_reports_missing_dependency(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "temporal_model.yaml"
    config_path.write_text("states: []", encoding="utf-8")

    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yaml":
            raise ModuleNotFoundError("No module named 'yaml'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="PyYAML"):
        load_markov_chain_model(config_path)
