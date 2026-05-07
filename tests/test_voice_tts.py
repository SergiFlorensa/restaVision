from __future__ import annotations

import wave
from pathlib import Path

from services.voice.tts import (
    CASTILIAN_NEUTRAL_VOICE_PROMPT,
    DEFAULT_KOKORO_MODEL_PATH,
    DEFAULT_KOKORO_SPANISH_VOICE,
    DEFAULT_KOKORO_VOICES_PATH,
    DEFAULT_PIPER_CONFIG_PATH,
    DEFAULT_PIPER_MODEL_PATH,
    DEFAULT_PIPER_SPANISH_VOICE,
    build_tts_adapter,
    prepare_text_for_tts,
)


def test_prepare_text_for_tts_normalizes_spacing_and_terminal_punctuation() -> None:
    assert prepare_text_for_tts("  A que hora   le gustaria  ") == ("A qué hora le gustaría.")
    assert prepare_text_for_tts("Puede repetirlo?") == "Disculpe. ¿Puede repetirlo?"


def test_prepare_text_for_tts_applies_spanish_pronunciation_hints() -> None:
    assert prepare_text_for_tts("Me confirma un telefono de contacto?") == (
        "Perfecto. ¿Me confirma un teléfono de contacto?"
    )
    assert prepare_text_for_tts("Si, puedo tomar nota de la situacion celiaca") == (
        "Sí, puedo tomar nota de la situación celíaca."
    )


def test_prepare_text_for_tts_expands_reservation_times_and_phones() -> None:
    assert prepare_text_for_tts(
        "Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222"
    ) == (
        "Perfecto. Reserva confirmada para dos personas el 2 de mayo a las "
        "nueve y media de la noche. Teléfono seis cero cero, uno uno uno, "
        "dos dos dos."
    )


def test_prepare_text_for_tts_applies_castilian_neutral_profile() -> None:
    assert (
        prepare_text_for_tts(
            "Piemontesa Paseo de Prim, diga",
            voice_profile="castilian_neutral",
        )
        == "Piemontesa Paseo de Prim, diga."
    )
    assert (
        prepare_text_for_tts(
            "Perfecto me dice el nombre?",
            voice_profile="castilian_neutral",
            style="neutral",
        )
        == "Perfecto. ¿Me dice su nombre?"
    )


def test_prepare_text_for_tts_applies_castilian_service_profile() -> None:
    assert build_tts_adapter("piper", voice_profile="castilian_service").config.speed == 0.99
    assert prepare_text_for_tts(
        "Entiendo. Lo compruebo un momento. Si quiere consultar la carta u otra informacion.",
        voice_profile="castilian_service",
    ).startswith("De acuerdo. Lo reviso un momento.")
    assert (
        prepare_text_for_tts(
            "Me confirma un numero de telefono de contacto?",
            voice_profile="castilian_service",
        )
        == "Perfecto. ¿Me confirma un teléfono de contacto?"
    )


def test_prepare_text_for_tts_does_not_pause_after_phone_label_without_digits() -> None:
    assert (
        prepare_text_for_tts(
            "Me confirma un telefono de contacto?",
            voice_profile="castilian_neutral",
        )
        == "Perfecto. ¿Me confirma un teléfono de contacto?"
    )


def test_prepare_text_for_tts_adds_castilian_information_focus() -> None:
    assert prepare_text_for_tts(
        "Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222",
        voice_profile="castilian_neutral",
    ) == (
        "Perfecto. Reserva confirmada: para dos personas, el 2 de mayo, a las "
        "nueve y media de la noche. Teléfono: seis cero cero, uno uno uno, "
        "dos dos dos."
    )


def test_prepare_text_for_tts_does_not_apply_repair_prefix_to_mixed_turn() -> None:
    assert (
        prepare_text_for_tts(
            "Piemontesa Paseo de Prim, diga. Puede repetirlo?",
            voice_profile="castilian_neutral",
        )
        == "Piemontesa Paseo de Prim, diga. ¿Puede repetirlo?"
    )


def test_mock_tts_adapter_writes_pcm16_wav(tmp_path: Path) -> None:
    output = tmp_path / "reply.wav"
    adapter = build_tts_adapter("mock")

    result = adapter.synthesize_to_file("A que hora le gustaria la reserva?", output)

    assert result.engine == "mock"
    assert result.output_path == str(output)
    assert result.duration_ms is not None
    assert result.duration_ms > 0
    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000


def test_cached_tts_adapter_reuses_generated_reply(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    first_output = tmp_path / "first.wav"
    second_output = tmp_path / "second.wav"
    adapter = build_tts_adapter("mock", cache_dir=cache_dir)

    first = adapter.synthesize_to_file("Perfecto, me dice el nombre?", first_output)
    second = adapter.synthesize_to_file("Perfecto, me dice el nombre?", second_output)

    assert first.metadata["cache_hit"] is False
    assert second.metadata["cache_hit"] is True
    assert first_output.exists()
    assert second_output.exists()
    assert len(list(cache_dir.glob("*.wav"))) == 1


def test_kokoro_adapter_uses_cpu_int8_defaults_without_loading_model() -> None:
    adapter = build_tts_adapter("kokoro_onnx", voice_profile="castilian_neutral")

    assert adapter.config.model_path == DEFAULT_KOKORO_MODEL_PATH
    assert adapter.config.voices_path == DEFAULT_KOKORO_VOICES_PATH
    assert adapter.config.voice == DEFAULT_KOKORO_SPANISH_VOICE
    assert adapter.config.language == "es"
    assert adapter.config.speed == 0.94
    assert adapter.config.voice_profile == "castilian_neutral"
    assert "espanol peninsular estandar" in CASTILIAN_NEUTRAL_VOICE_PROMPT


def test_piper_adapter_uses_es_es_defaults_without_loading_model() -> None:
    adapter = build_tts_adapter("piper", voice_profile="castilian_neutral")

    assert adapter.config.model_path == DEFAULT_PIPER_MODEL_PATH
    assert adapter.config.voices_path == DEFAULT_PIPER_CONFIG_PATH
    assert adapter.config.voice == DEFAULT_PIPER_SPANISH_VOICE
    assert adapter.config.language == "es"
    assert adapter.config.speed == 0.94
    assert adapter.config.voice_profile == "castilian_neutral"


def test_build_tts_adapter_rejects_unknown_engine() -> None:
    try:
        build_tts_adapter("unknown")
    except ValueError as exc:
        assert "Unsupported TTS engine" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
