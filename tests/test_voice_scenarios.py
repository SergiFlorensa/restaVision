from __future__ import annotations

from services.voice.scenarios import classify_voice_scenario


def test_voice_scenarios_note_zone_preference_without_forced_manager_transfer() -> None:
    scenario = classify_voice_scenario("mesa cerca de la ventana y zona tranquila")

    assert scenario is not None
    assert scenario.scenario_id == "terrace"
    assert scenario.requires_manager is False
    assert "preferencia de zona" in scenario.reply_text


def test_voice_scenarios_route_party_size_changes_to_manager() -> None:
    scenario = classify_voice_scenario("queria anadir personas a mi reserva")

    assert scenario is not None
    assert scenario.scenario_id == "party_size_change"
    assert scenario.requires_manager is True
    assert scenario.interrupts_reservation is True


def test_voice_scenarios_route_complaints_to_manager() -> None:
    scenario = classify_voice_scenario("llamo por una queja de la comida")

    assert scenario is not None
    assert scenario.scenario_id == "complaint"
    assert scenario.requires_manager is True
    assert scenario.interrupts_reservation is True
