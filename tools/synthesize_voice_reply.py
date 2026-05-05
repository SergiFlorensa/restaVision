from __future__ import annotations

import argparse
import json
import sys
import wave
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.voice.tts import (
        DEFAULT_KOKORO_MODEL_PATH,
        DEFAULT_KOKORO_VOICES_PATH,
        DEFAULT_PIPER_CONFIG_PATH,
        DEFAULT_PIPER_MODEL_PATH,
        VOICE_RENDERING_PROFILES,
        build_tts_adapter,
    )

    parser = argparse.ArgumentParser(
        description="Genera audio local desde una respuesta textual del agente."
    )
    parser.add_argument(
        "--text",
        default="A que hora le gustaria la reserva?",
        help="Texto que debe pronunciar el motor TTS.",
    )
    parser.add_argument(
        "--engine",
        default="piper",
        choices=("kokoro_onnx", "piper", "windows_sapi", "mock"),
    )
    parser.add_argument("--output", type=Path, default=Path("data/local_samples/tts_last.wav"))
    parser.add_argument(
        "--model-path",
        default=None,
        help=(
            "Ruta del modelo. Por defecto usa Piper es_ES davefx si --engine=piper "
            "o Kokoro int8 si --engine=kokoro_onnx."
        ),
    )
    parser.add_argument(
        "--voices-path",
        default=None,
        help=("Ruta de voces/config. En Piper apunta al .onnx.json; en Kokoro al voices-v1.0.bin."),
    )
    parser.add_argument(
        "--voice",
        default=None,
        help=(
            "Voz del motor. Kokoro usa ef_dora por defecto; Windows SAPI usa la "
            "voz instalada por defecto si se omite."
        ),
    )
    parser.add_argument("--language", default="es")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument(
        "--voice-profile",
        default="castilian_neutral",
        choices=tuple(sorted(VOICE_RENDERING_PROFILES)),
        help="Perfil de voz previo al TTS. castilian_neutral ajusta cadencia y velocidad.",
    )
    parser.add_argument(
        "--style",
        default="auto",
        choices=("auto", "neutral", "warm", "confirmation", "repair", "serious"),
        help="Estilo prosodico previo al TTS.",
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/local_samples/tts_cache"))
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--play", action="store_true")
    args = parser.parse_args()
    model_path = args.model_path
    voices_path = args.voices_path
    if args.engine == "piper":
        model_path = model_path or DEFAULT_PIPER_MODEL_PATH
        voices_path = voices_path or DEFAULT_PIPER_CONFIG_PATH
    elif args.engine == "kokoro_onnx":
        model_path = model_path or DEFAULT_KOKORO_MODEL_PATH
        voices_path = voices_path or DEFAULT_KOKORO_VOICES_PATH

    adapter = build_tts_adapter(
        args.engine,
        model_path=model_path,
        voices_path=voices_path,
        voice=args.voice,
        language=args.language,
        speed=args.speed,
        style=args.style,
        voice_profile=args.voice_profile,
        cache_dir=None if args.no_cache else args.cache_dir,
    )
    result = adapter.synthesize_to_file(args.text, args.output)
    if args.play:
        _play_wav(args.output)
    print(json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2))


def _play_wav(path: Path) -> None:
    try:
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return
    except ModuleNotFoundError:
        pass

    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise SystemExit("No se puede reproducir audio: falta sounddevice.") from exc

    samples, sample_rate = _read_pcm16_wav(path)
    sd.play(samples, sample_rate)
    sd.wait()


def _read_pcm16_wav(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())
    if sample_width != 2:
        raise ValueError("Solo se puede reproducir PCM16 WAV en esta utilidad.")
    samples: list[float] = []
    for index in range(0, len(frames), 2 * channels):
        value = int.from_bytes(frames[index : index + 2], "little", signed=True)
        samples.append(value / 32768)
    return samples, sample_rate


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
