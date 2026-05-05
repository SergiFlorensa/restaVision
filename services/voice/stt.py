from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SpeechToTextConfig:
    engine: str
    model_path: str | None = None
    executable_path: str | None = None
    language: str = "es"
    timeout_seconds: float = 45.0
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    start_ms: int | None
    end_ms: int | None
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    transcript: str
    engine: str
    model: str | None
    language: str | None
    processing_ms: int
    confidence: float | None = None
    segments: tuple[TranscriptionSegment, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


class SpeechToTextAdapter(Protocol):
    config: SpeechToTextConfig

    def transcribe(self, wav_path: str | Path) -> TranscriptionResult: ...


class MockSpeechToTextAdapter:
    def __init__(
        self,
        transcripts: Mapping[str, str] | None = None,
        *,
        default_transcript: str = "",
        confidence: float = 0.95,
    ) -> None:
        self.config = SpeechToTextConfig(engine="mock")
        self._transcripts = dict(transcripts or {})
        self._default_transcript = default_transcript
        self._confidence = confidence

    def transcribe(self, wav_path: str | Path) -> TranscriptionResult:
        started = perf_counter()
        path = Path(wav_path)
        transcript = self._transcripts.get(path.name, self._default_transcript)
        return TranscriptionResult(
            transcript=transcript,
            engine=self.config.engine,
            model=None,
            language="es",
            processing_ms=_elapsed_ms(started),
            confidence=self._confidence,
            segments=(TranscriptionSegment(None, None, transcript),) if transcript else (),
        )


class WhisperCppSpeechToTextAdapter:
    """Optional whisper.cpp wrapper.

    The adapter intentionally talks to an external binary so the project does
    not import heavy ML dependencies unless the user installs them.
    """

    def __init__(self, config: SpeechToTextConfig) -> None:
        if not config.executable_path:
            raise ValueError("whisper.cpp adapter requires executable_path.")
        if not config.model_path:
            raise ValueError("whisper.cpp adapter requires model_path.")
        self.config = config

    def transcribe(self, wav_path: str | Path) -> TranscriptionResult:
        started = perf_counter()
        command = [
            str(self.config.executable_path),
            "-m",
            str(self.config.model_path),
            "-f",
            str(wav_path),
            "-l",
            self.config.language,
            "-nt",
        ]
        command.extend(self.config.extra_args)
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=self.config.timeout_seconds,
        )
        output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
        if completed.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed with code {completed.returncode}: {output}")
        transcript = _clean_whisper_cpp_output(completed.stdout)
        return TranscriptionResult(
            transcript=transcript,
            engine=self.config.engine,
            model=self.config.model_path,
            language=self.config.language,
            processing_ms=_elapsed_ms(started),
            confidence=None,
            segments=(TranscriptionSegment(None, None, transcript),) if transcript else (),
            metadata={"returncode": completed.returncode},
        )


class VoskSpeechToTextAdapter:
    """Optional Vosk wrapper for low-latency local CPU baselines."""

    def __init__(self, config: SpeechToTextConfig) -> None:
        if not config.model_path:
            raise ValueError("Vosk adapter requires model_path.")
        self.config = config
        self._model: object | None = None

    def _get_model(self) -> object:
        if self._model is None:
            try:
                from vosk import Model
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Vosk is not installed. Install requirements/audio.txt."
                ) from exc
            self._model = Model(str(self.config.model_path))
        return self._model

    def transcribe(self, wav_path: str | Path) -> TranscriptionResult:
        started = perf_counter()
        try:
            import wave

            from vosk import KaldiRecognizer
        except ModuleNotFoundError as exc:
            raise RuntimeError("Vosk is not installed. Install requirements/audio.txt.") from exc

        with wave.open(str(wav_path), "rb") as wav_file:
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise ValueError("Vosk adapter expects mono PCM16 WAV.")
            recognizer = KaldiRecognizer(self._get_model(), wav_file.getframerate())
            chunks: list[str] = []
            while True:
                data = wav_file.readframes(4000)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    chunks.append(json.loads(recognizer.Result()).get("text", ""))
            chunks.append(json.loads(recognizer.FinalResult()).get("text", ""))

        transcript = " ".join(chunk.strip() for chunk in chunks if chunk.strip())
        return TranscriptionResult(
            transcript=transcript,
            engine=self.config.engine,
            model=self.config.model_path,
            language=self.config.language,
            processing_ms=_elapsed_ms(started),
            confidence=None,
            segments=(TranscriptionSegment(None, None, transcript),) if transcript else (),
        )


def build_stt_adapter(
    engine: str,
    *,
    model_path: str | None = None,
    executable_path: str | None = None,
    language: str = "es",
    timeout_seconds: float = 45.0,
    mock_transcripts: Mapping[str, str] | None = None,
    mock_default_transcript: str = "",
) -> SpeechToTextAdapter:
    normalized_engine = engine.strip().lower()
    if normalized_engine == "mock":
        return MockSpeechToTextAdapter(
            mock_transcripts,
            default_transcript=mock_default_transcript,
        )
    config = SpeechToTextConfig(
        engine=normalized_engine,
        model_path=model_path,
        executable_path=executable_path,
        language=language,
        timeout_seconds=timeout_seconds,
    )
    if normalized_engine in {"whisper.cpp", "whisper_cpp", "whisper-cpp"}:
        return WhisperCppSpeechToTextAdapter(config)
    if normalized_engine == "vosk":
        return VoskSpeechToTextAdapter(config)
    raise ValueError(f"Unsupported STT engine: {engine}")


def _clean_whisper_cpp_output(output: str) -> str:
    lines: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("whisper_"):
            continue
        if stripped.startswith("[") and "]" in stripped:
            stripped = stripped.split("]", 1)[1].strip()
        if stripped:
            lines.append(stripped)
    return " ".join(lines).strip()


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
