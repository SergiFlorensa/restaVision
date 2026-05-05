from __future__ import annotations

import math
import wave
from pathlib import Path

from services.voice.stt import MockSpeechToTextAdapter, build_stt_adapter
from services.voice.stt_benchmark import SttBenchmarkCase, run_stt_benchmark


def test_mock_stt_adapter_returns_filename_transcript(tmp_path: Path) -> None:
    wav_path = tmp_path / "reserva.wav"
    _write_voice_wav(wav_path)
    adapter = MockSpeechToTextAdapter({wav_path.name: "Reserva para 2 a las 20:00"})

    result = adapter.transcribe(wav_path)

    assert result.engine == "mock"
    assert result.transcript == "Reserva para 2 a las 20:00"
    assert result.processing_ms >= 0
    assert result.confidence == 0.95


def test_build_stt_adapter_rejects_unknown_engine() -> None:
    try:
        build_stt_adapter("unknown")
    except ValueError as exc:
        assert "Unsupported STT engine" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_stt_benchmark_runs_quality_gate_and_voice_agent(tmp_path: Path) -> None:
    wav_path = tmp_path / "reserva.wav"
    _write_voice_wav(wav_path)
    transcript = "Reserva para 2 a las 20:00 a nombre de Lara telefono 600111222"
    adapter = MockSpeechToTextAdapter({wav_path.name: transcript})

    report = run_stt_benchmark(
        (
            SttBenchmarkCase(
                case_id="reservation",
                wav_path=str(wav_path),
                expected_transcript=transcript,
                expected_intent="create_reservation",
                expected_action_name="utter_confirm_customer_name",
                expected_slots={
                    "party_size": 2,
                    "customer_name": "Lara",
                    "phone": "600111222",
                },
            ),
        ),
        adapter,
    )

    assert report.sample_count == 1
    assert report.accepted_count == 1
    assert report.blocked_count == 0
    assert report.average_wer == 0.0
    assert report.intent_accuracy == 1.0
    assert report.action_accuracy == 1.0
    assert report.slot_field_accuracy == 1.0
    assert report.cases[0].accepted_for_agent is True
    assert report.cases[0].voice_intent == "create_reservation"


def test_stt_benchmark_blocks_silence_before_voice_agent(tmp_path: Path) -> None:
    wav_path = tmp_path / "silence.wav"
    _write_silence_wav(wav_path)
    adapter = MockSpeechToTextAdapter({wav_path.name: "Reserva para 2 a las 20:00"})

    report = run_stt_benchmark(
        (
            SttBenchmarkCase(
                case_id="silence",
                wav_path=str(wav_path),
                expected_transcript="Reserva para 2 a las 20:00",
            ),
        ),
        adapter,
    )

    assert report.sample_count == 1
    assert report.accepted_count == 0
    assert report.blocked_count == 1
    assert report.cases[0].vad.has_speech is False
    assert report.cases[0].voice_intent is None


def _write_voice_wav(path: Path, sample_rate: int = 16000) -> None:
    samples = [
        0.22 * math.sin(2 * math.pi * 220 * index / sample_rate) for index in range(sample_rate)
    ]
    _write_wav(path, samples, sample_rate)


def _write_silence_wav(path: Path, sample_rate: int = 16000) -> None:
    _write_wav(path, [0.0] * sample_rate, sample_rate)


def _write_wav(path: Path, samples: list[float], sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, sample))
            frames.extend(int(clipped * 32767).to_bytes(2, "little", signed=True))
        wav_file.writeframes(bytes(frames))
