from __future__ import annotations

from services.maria.instructions import MariaInstructionParser, MariaIntent


def test_instruction_parser_detects_table_attention_intent_and_table_id() -> None:
    parser = MariaInstructionParser()

    instruction = parser.parse("Maria revisa si la mesa 4 lleva mucho sin atencion")

    assert instruction.intent is MariaIntent.TABLE_ATTENTION
    assert instruction.table_id == "table_04"
    assert instruction.requires_multimodal_capture is True


def test_instruction_parser_detects_cleanliness_and_zone_hint() -> None:
    parser = MariaInstructionParser()

    instruction = parser.parse("Comprueba limpieza en barra y mesas cercanas")

    assert instruction.intent is MariaIntent.TABLE_CLEANLINESS
    assert instruction.zone_hint == "barra"


def test_instruction_parser_falls_back_to_generic_review() -> None:
    parser = MariaInstructionParser()

    instruction = parser.parse("Necesito una revision rapida")

    assert instruction.intent is MariaIntent.GENERIC_REVIEW
    assert instruction.table_id is None
