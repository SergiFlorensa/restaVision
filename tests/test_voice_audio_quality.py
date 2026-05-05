from __future__ import annotations

import math
import wave
from pathlib import Path

from apps.api.main import create_app
from fastapi.testclient import TestClient
from services.events.service import RestaurantMVPService
from services.voice.audio_quality import (
    evaluate_transcript_quality,
    read_pcm16_wav,
    simple_energy_vad,
    word_error_rate,
)


def test_simple_energy_vad_rejects_silence(tmp_path: Path) -> None:
    wav_path = tmp_path / "silence.wav"
    _write_wav(wav_path, [0.0] * 16000)

    read_result = read_pcm16_wav(wav_path)
    vad = simple_energy_vad(read_result.audio, read_result.samples)

    assert read_result.audio.sample_rate_hz == 16000
    assert vad.has_speech is False
    assert vad.reason == "speech_too_short"


def test_simple_energy_vad_accepts_clear_voice_like_signal(tmp_path: Path) -> None:
    wav_path = tmp_path / "voice.wav"
    samples = [0.22 * math.sin(2 * math.pi * 220 * index / 16000) for index in range(16000)]
    _write_wav(wav_path, samples)

    read_result = read_pcm16_wav(wav_path)
    vad = simple_energy_vad(read_result.audio, read_result.samples)

    assert vad.has_speech is True
    assert vad.speech_ratio > 0.9
    assert vad.segments


def test_transcript_quality_rejects_repetition_and_low_confidence() -> None:
    quality = evaluate_transcript_quality(
        "ruido ruido ruido ruido ruido",
        confidence=0.3,
    )

    assert quality.accepted is False
    assert "repetitive_transcript" in quality.reasons
    assert "low_stt_confidence" in quality.reasons


def test_transcript_quality_accepts_repetitive_phone_when_expected() -> None:
    quality = evaluate_transcript_quality(
        "seis seis seis cero cero cero seis seis seis",
        allow_phone_number=True,
    )

    assert quality.accepted is True
    assert quality.normalized_text == "6 6 6 0 0 0 6 6 6"


def test_transcript_quality_still_rejects_repetitive_phone_when_not_expected() -> None:
    quality = evaluate_transcript_quality("seis seis seis cero cero cero seis seis seis")

    assert quality.accepted is False
    assert "repetitive_transcript" in quality.reasons


def test_transcript_quality_rejects_short_phone_even_when_expected() -> None:
    quality = evaluate_transcript_quality(
        "seis seis seis seis seis seis seis",
        allow_phone_number=True,
    )

    assert quality.accepted is False
    assert "repetitive_transcript" in quality.reasons


def test_spanish_word_error_rate_normalizes_fillers_and_number_words() -> None:
    wer = word_error_rate(
        "Reserva para cuatro personas a las nueve",
        "eh reserva para 4 personas a las 9",
    )

    assert wer == 0.0


def test_voice_audio_quality_endpoint_blocks_silence(tmp_path: Path) -> None:
    wav_path = tmp_path / "silence.wav"
    _write_wav(wav_path, [0.0] * 16000)
    client = TestClient(create_app(RestaurantMVPService()))

    response = client.post(
        "/api/v1/voice/audio/quality",
        json={
            "wav_path": str(wav_path),
            "transcript": "Reserva para cuatro personas",
            "confidence": 0.92,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["vad"]["has_speech"] is False
    assert payload["accepted_for_agent"] is False
    assert "speech_too_short" in payload["blocking_reasons"]


def test_voice_audio_quality_endpoint_accepts_clear_audio_and_transcript(tmp_path: Path) -> None:
    wav_path = tmp_path / "voice.wav"
    samples = [0.22 * math.sin(2 * math.pi * 220 * index / 16000) for index in range(16000)]
    _write_wav(wav_path, samples)
    client = TestClient(create_app(RestaurantMVPService()))

    response = client.post(
        "/api/v1/voice/audio/quality",
        json={
            "wav_path": str(wav_path),
            "transcript": "Reserva para cuatro personas a las nueve",
            "reference_text": "Reserva para 4 personas a las 9",
            "confidence": 0.92,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["vad"]["has_speech"] is True
    assert payload["transcript_quality"]["accepted"] is True
    assert payload["transcript_quality"]["wer"] == 0.0
    assert payload["accepted_for_agent"] is True
    assert payload["recommendation"] == "send_to_voice_agent"


def _write_wav(path: Path, samples: list[float], sample_rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, sample))
            frames.extend(int(clipped * 32767).to_bytes(2, "little", signed=True))
        wav_file.writeframes(bytes(frames))
