from __future__ import annotations

from services.voice.reply_catalog import (
    VOICE_REPLY_TEMPLATES,
    export_voice_reply_catalog,
    render_voice_reply,
)


def test_voice_reply_catalog_contains_hot_path_reservation_actions() -> None:
    expected_actions = {
        "utter_ask_party_size",
        "utter_ask_requested_time",
        "utter_ask_customer_name",
        "utter_confirm_customer_name",
        "utter_ask_phone",
        "action_confirm_reservation",
    }

    assert expected_actions.issubset(VOICE_REPLY_TEMPLATES)


def test_voice_reply_catalog_renders_slot_values_without_llm() -> None:
    text = render_voice_reply(
        "action_confirm_reservation",
        party_size=2,
        spoken_time="a las 21:30",
        customer_name="Sergi",
    )

    assert "2 personas" in text
    assert "a las 21:30" in text
    assert "Sergi" in text
    assert "Piemontesa de Passeig de Prim" in text


def test_voice_reply_catalog_exports_slot_metadata() -> None:
    exported = export_voice_reply_catalog()
    confirm_entry = next(
        item for item in exported if item["action_name"] == "utter_confirm_customer_name"
    )

    assert confirm_entry["slot_names"] == ["customer_name"]
    assert confirm_entry["latency_tier"] == "hot_path"


def test_voice_reply_catalog_bridge_mentions_menu_web_without_raw_url() -> None:
    text = render_voice_reply("utter_background_advice_bridge")

    assert "La Piemontesa" in text
    assert "La Piemontesa Reus" not in text
    assert "carta u otra informacion del restaurante" in text
    assert "https://" not in text
