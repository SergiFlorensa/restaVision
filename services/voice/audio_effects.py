from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

DEFAULT_VOICE_POSTPROCESSOR_SOURCE = Path("tools/native/voice_postprocess.rs")
DEFAULT_VOICE_POSTPROCESSOR_EXE = Path("tools/native/voice_postprocess.exe")
VOICE_POSTPROCESS_PRESETS = ("none", "clarity", "warm", "phone")


@dataclass(frozen=True, slots=True)
class VoicePostprocessResult:
    applied: bool
    preset: str
    input_path: str
    output_path: str
    elapsed_ms: int
    processor: str = "none"
    metadata: dict[str, object] = field(default_factory=dict)


def postprocess_voice_wav(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preset: str = "none",
    processor_path: str | Path | None = None,
    auto_build: bool = True,
) -> VoicePostprocessResult:
    started = perf_counter()
    normalized_preset = preset.strip().lower()
    input_wav = Path(input_path)
    output_wav = Path(output_path) if output_path is not None else input_wav
    if normalized_preset in {"", "none", "off", "disabled"}:
        return VoicePostprocessResult(
            applied=False,
            preset="none",
            input_path=str(input_wav),
            output_path=str(output_wav),
            elapsed_ms=_elapsed_ms(started),
            metadata={"reason": "disabled"},
        )
    if normalized_preset not in VOICE_POSTPROCESS_PRESETS:
        raise ValueError(f"Unsupported voice postprocess preset: {preset}")

    processor = _resolve_voice_postprocessor(processor_path, auto_build=auto_build)
    actual_output = output_wav
    replace_input = input_wav.resolve() == output_wav.resolve()
    if replace_input:
        actual_output = output_wav.with_suffix(f".{normalized_preset}.tmp.wav")
    actual_output.parent.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        [str(processor), str(input_wav), str(actual_output), normalized_preset],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if replace_input:
        shutil.move(str(actual_output), str(output_wav))
    metadata = _parse_processor_stdout(completed.stdout)
    if completed.stderr.strip():
        metadata["stderr"] = completed.stderr.strip()[:400]
    return VoicePostprocessResult(
        applied=True,
        preset=normalized_preset,
        input_path=str(input_wav),
        output_path=str(output_wav),
        elapsed_ms=_elapsed_ms(started),
        processor=str(processor),
        metadata=metadata,
    )


def _resolve_voice_postprocessor(
    processor_path: str | Path | None,
    *,
    auto_build: bool,
) -> Path:
    if processor_path is not None:
        processor = Path(processor_path)
        if processor.exists():
            return processor
        raise FileNotFoundError(f"Voice postprocessor not found: {processor}")
    if DEFAULT_VOICE_POSTPROCESSOR_EXE.exists():
        return DEFAULT_VOICE_POSTPROCESSOR_EXE
    if auto_build:
        return _build_voice_postprocessor()
    raise FileNotFoundError(
        "Voice postprocessor executable not found. Build tools/native/voice_postprocess.rs first."
    )


def _build_voice_postprocessor() -> Path:
    rustc = shutil.which("rustc") or str(Path.home() / ".cargo/bin/rustc.exe")
    rustc_path = Path(rustc)
    if not rustc_path.exists() and shutil.which("rustc") is None:
        raise RuntimeError(
            "rustc not found. Install Rust or build the voice postprocessor manually."
        )
    DEFAULT_VOICE_POSTPROCESSOR_EXE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(rustc_path) if rustc_path.exists() else "rustc",
            str(DEFAULT_VOICE_POSTPROCESSOR_SOURCE),
            "-O",
            "-o",
            str(DEFAULT_VOICE_POSTPROCESSOR_EXE),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return DEFAULT_VOICE_POSTPROCESSOR_EXE


def _parse_processor_stdout(stdout: str) -> dict[str, object]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text.splitlines()[-1])
    except json.JSONDecodeError:
        return {"stdout": text[:400]}
    if isinstance(parsed, dict):
        return parsed
    return {"stdout": text[:400]}


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
