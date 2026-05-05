from __future__ import annotations

import argparse
import json
import sys
import wave
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.events.service import RestaurantMVPService
    from services.voice.agent import VoiceReservationAgent
    from services.voice.audio_quality import (
        evaluate_transcript_quality,
        read_pcm16_wav,
        simple_energy_vad,
    )
    from services.voice.stt import build_stt_adapter

    parser = argparse.ArgumentParser(
        description="Graba microfono local, transcribe y muestra respuesta del agente."
    )
    parser.add_argument("--seconds", type=float, default=7.0)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/local_samples/mic_last.wav"))
    parser.add_argument("--engine", default="vosk", choices=("vosk", "mock"))
    parser.add_argument(
        "--model-path",
        default="models/checkpoints/vosk-model-small-es-0.42",
    )
    parser.add_argument("--mock-transcript", default="")
    args = parser.parse_args()

    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise SystemExit("sounddevice no esta instalado. Ejecuta requirements/audio.txt") from exc

    if args.list_devices:
        print(sd.query_devices())
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"Grabando {args.seconds:.1f}s. Habla ahora...")
    recording = sd.rec(
        int(args.seconds * args.sample_rate),
        samplerate=args.sample_rate,
        channels=1,
        dtype="int16",
        device=args.device,
    )
    sd.wait()
    _write_pcm16_wav(args.output, recording, sample_rate=args.sample_rate)
    print(f"Audio guardado en {args.output}")

    read_result = read_pcm16_wav(args.output)
    vad = simple_energy_vad(read_result.audio, read_result.samples)
    adapter = build_stt_adapter(
        args.engine,
        model_path=args.model_path,
        mock_default_transcript=args.mock_transcript,
    )
    stt = adapter.transcribe(args.output)
    transcript_quality = evaluate_transcript_quality(
        stt.transcript,
        confidence=stt.confidence,
    )
    response: dict[str, object] = {
        "audio": read_result.audio,
        "vad": vad,
        "stt": stt,
        "transcript_quality": transcript_quality,
        "accepted_for_agent": vad.has_speech and transcript_quality.accepted,
    }

    if vad.has_speech and transcript_quality.accepted:
        agent = VoiceReservationAgent(RestaurantMVPService())
        call = agent.start_call(source_channel="local_microphone", started_at=datetime.now(UTC))
        turn = agent.handle_turn(
            call.call_id,
            transcript=stt.transcript,
            confidence=stt.confidence or 0.95,
            observed_at=datetime.now(UTC),
        )
        response["agent"] = {
            "intent": str(turn.intent),
            "action_name": turn.action_name,
            "missing_fields": list(turn.missing_fields),
            "reply_text": turn.reply_text,
            "escalated": turn.escalated,
            "reservation_draft": asdict(turn.call.reservation_draft),
        }
    else:
        response["agent"] = {
            "skipped": True,
            "reason": "vad_or_transcript_quality_blocked",
        }

    print(json.dumps(_to_jsonable(response), ensure_ascii=False, indent=2))


def _write_pcm16_wav(path: Path, recording: Any, *, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(recording.tobytes())


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
