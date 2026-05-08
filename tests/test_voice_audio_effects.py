from __future__ import annotations

import shutil
import wave
from pathlib import Path

import pytest
from services.voice.audio_effects import postprocess_voice_wav


def test_voice_postprocess_disabled_returns_original_path(tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    _write_test_wav(input_path)

    result = postprocess_voice_wav(input_path, preset="none")

    assert result.applied is False
    assert result.preset == "none"
    assert result.output_path == str(input_path)


def test_voice_postprocess_rejects_unknown_preset(tmp_path: Path) -> None:
    input_path = tmp_path / "input.wav"
    _write_test_wav(input_path)

    with pytest.raises(ValueError, match="Unsupported voice postprocess preset"):
        postprocess_voice_wav(input_path, preset="extreme")


def test_rust_voice_postprocess_writes_pcm16_output(tmp_path: Path) -> None:
    if shutil.which("rustc") is None and not (Path.home() / ".cargo/bin/rustc.exe").exists():
        pytest.skip("rustc is not available")
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    _write_test_wav(input_path)

    result = postprocess_voice_wav(input_path, output_path, preset="clarity")

    assert result.applied is True
    assert result.preset == "clarity"
    assert result.metadata["preset"] == "clarity"
    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() > 0


def _write_test_wav(path: Path) -> None:
    sample_rate = 16000
    frames = bytearray()
    for index in range(sample_rate // 4):
        value = int(12000 * ((index % 80) / 80.0 - 0.5))
        frames.extend(value.to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))
