from __future__ import annotations

from services.voice.response_compressor import (
    OllamaVoiceReplyCompressor,
    VoiceReplyCompressionConfig,
    VoiceReplyCompressor,
    build_voice_reply_compressor,
)


def test_disabled_voice_reply_compressor_returns_original_text() -> None:
    compressor = VoiceReplyCompressor()

    result = compressor.compress("Reserva confirmada para dos personas.")

    assert result.output_text == "Reserva confirmada para dos personas."
    assert result.applied is False
    assert result.provider == "none"


def test_build_voice_reply_compressor_rejects_unknown_provider() -> None:
    try:
        build_voice_reply_compressor("remote_paid")
    except ValueError as exc:
        assert "Unsupported voice reply compressor provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_ollama_compressor_accepts_safe_shorter_rewrite() -> None:
    compressor = _FakeOllamaCompressor("Perfecto. Reserva confirmada para 2 personas a las 21:30.")

    result = compressor.compress(
        "Reserva confirmada para 2 personas a las 21:30, a nombre de Sergio. Gracias."
    )

    assert result.applied is True
    assert result.output_text == "Perfecto. Reserva confirmada para 2 personas a las 21:30."


def test_ollama_compressor_rejects_rewrite_that_drops_critical_tokens() -> None:
    compressor = _FakeOllamaCompressor("Perfecto. Reserva confirmada para dos personas.")

    result = compressor.compress(
        "Reserva confirmada para 2 personas a las 21:30, a nombre de Sergio. Gracias."
    )

    assert result.applied is False
    assert result.output_text.startswith("Reserva confirmada para 2 personas")
    assert str(result.metadata["reason"]).startswith("missing_critical_tokens")


def test_ollama_compressor_falls_back_when_ollama_fails() -> None:
    compressor = _FailingOllamaCompressor()

    result = compressor.compress("A que nombre dejamos la reserva?")

    assert result.applied is False
    assert result.output_text == "A que nombre dejamos la reserva?"
    assert result.metadata["fallback_reason"] == "OSError"


def test_ollama_compressor_uses_fast_rule_before_llm_for_known_reply() -> None:
    compressor = _FailingOllamaCompressor(enable_fast_path=True)

    result = compressor.compress(
        "No he entendido bien el telefono. Digamelo de nuevo, por favor, "
        "con los nueve digitos seguidos."
    )

    assert result.provider == "rules"
    assert result.applied is True
    assert result.output_text == (
        "No he entendido bien el telefono. Digame los nueve digitos, por favor."
    )


class _FakeOllamaCompressor(OllamaVoiceReplyCompressor):
    def __init__(self, generated_text: str) -> None:
        super().__init__(
            VoiceReplyCompressionConfig(
                provider="ollama",
                model="fake",
                enable_fast_path=False,
            )
        )
        self._generated_text = generated_text

    def _call_ollama(self, text: str) -> str:
        return self._generated_text


class _FailingOllamaCompressor(OllamaVoiceReplyCompressor):
    def __init__(self, *, enable_fast_path: bool = False) -> None:
        super().__init__(
            VoiceReplyCompressionConfig(
                provider="ollama",
                model="fake",
                enable_fast_path=enable_fast_path,
            )
        )

    def _call_ollama(self, text: str) -> str:
        raise OSError("ollama unavailable")
