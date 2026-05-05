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
    from services.voice.tts import (
        DEFAULT_KOKORO_MODEL_PATH,
        DEFAULT_KOKORO_VOICES_PATH,
        DEFAULT_PIPER_CONFIG_PATH,
        DEFAULT_PIPER_MODEL_PATH,
        VOICE_RENDERING_PROFILES,
        build_tts_adapter,
    )

    parser = argparse.ArgumentParser(
        description="Sesion local interactiva: microfono -> STT -> agente -> TTS."
    )
    parser.add_argument("--seconds", type=float, default=7.0)
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--max-turns", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=Path("data/local_samples/interactive"))
    parser.add_argument("--stt-engine", default="vosk", choices=("vosk", "mock"))
    parser.add_argument(
        "--stt-model-path",
        default="models/checkpoints/vosk-model-small-es-0.42",
    )
    parser.add_argument("--mock-transcript", default="")
    parser.add_argument(
        "--tts-engine",
        default="piper",
        choices=("none", "kokoro_onnx", "piper", "windows_sapi", "mock"),
    )
    parser.add_argument("--tts-model-path", default=None)
    parser.add_argument("--tts-voices-path", default=None)
    parser.add_argument(
        "--tts-voice",
        default=None,
        help=(
            "Voz del motor TTS. Kokoro usa ef_dora por defecto; Windows SAPI usa "
            "la voz instalada por defecto si se omite."
        ),
    )
    parser.add_argument("--tts-language", default="es")
    parser.add_argument("--tts-speed", type=float, default=1.0)
    parser.add_argument(
        "--tts-voice-profile",
        default="castilian_neutral",
        choices=tuple(sorted(VOICE_RENDERING_PROFILES)),
        help=(
            "Perfil de voz. castilian_neutral ajusta cadencia y velocidad para "
            "restaurante en Espana."
        ),
    )
    parser.add_argument(
        "--tts-style",
        default="auto",
        choices=("auto", "neutral", "warm", "confirmation", "repair", "serious"),
        help="Estilo prosodico previo al TTS.",
    )
    parser.add_argument("--tts-cache-dir", type=Path, default=Path("data/local_samples/tts_cache"))
    parser.add_argument("--no-tts-cache", action="store_true")
    parser.add_argument(
        "--opening-greeting",
        default="Piemontesa Paseo de Prim, diga.",
        help="Saludo inicial que el agente dice al descolgar la llamada simulada.",
    )
    parser.add_argument("--skip-opening-greeting", action="store_true")
    parser.add_argument("--play", action="store_true")
    args = parser.parse_args()

    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise SystemExit("sounddevice no esta instalado. Ejecuta requirements/audio.txt") from exc

    if args.list_devices:
        print(sd.query_devices())
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stt_adapter = build_stt_adapter(
        args.stt_engine,
        model_path=args.stt_model_path,
        mock_default_transcript=args.mock_transcript,
    )
    tts_adapter = None
    if args.tts_engine != "none":
        tts_model_path = args.tts_model_path
        tts_voices_path = args.tts_voices_path
        if args.tts_engine == "piper":
            tts_model_path = tts_model_path or DEFAULT_PIPER_MODEL_PATH
            tts_voices_path = tts_voices_path or DEFAULT_PIPER_CONFIG_PATH
        elif args.tts_engine == "kokoro_onnx":
            tts_model_path = tts_model_path or DEFAULT_KOKORO_MODEL_PATH
            tts_voices_path = tts_voices_path or DEFAULT_KOKORO_VOICES_PATH
        tts_adapter = build_tts_adapter(
            args.tts_engine,
            model_path=tts_model_path,
            voices_path=tts_voices_path,
            voice=args.tts_voice,
            language=args.tts_language,
            speed=args.tts_speed,
            style=args.tts_style,
            voice_profile=args.tts_voice_profile,
            cache_dir=None if args.no_tts_cache else args.tts_cache_dir,
        )

    agent = VoiceReservationAgent(RestaurantMVPService())
    call = agent.start_call(source_channel="local_interactive_microphone")
    print(f"Llamada local iniciada: {call.call_id}")
    if tts_adapter is not None and args.opening_greeting.strip() and not args.skip_opening_greeting:
        greeting_path = args.output_dir / "turn_00_opening_greeting.wav"
        greeting_tts = tts_adapter.synthesize_to_file(args.opening_greeting, greeting_path)
        print(f"Agente: {greeting_tts.text}")
        if args.play:
            _play_wav(greeting_path, sounddevice_module=sd)
    print("Pulsa Enter para grabar cada turno. Escribe q y Enter para salir.")

    for turn_number in range(1, args.max_turns + 1):
        command = input(f"\nTurno {turn_number}/{args.max_turns}> ")
        if command.strip().lower() in {"q", "quit", "salir"}:
            break

        wav_path = args.output_dir / f"turn_{turn_number:02d}_input.wav"
        print(f"Grabando {args.seconds:.1f}s...")
        _record_wav(
            wav_path,
            seconds=args.seconds,
            sample_rate=args.sample_rate,
            device=args.device,
            sounddevice_module=sd,
        )

        read_result = read_pcm16_wav(wav_path)
        vad = simple_energy_vad(read_result.audio, read_result.samples)
        stt = stt_adapter.transcribe(wav_path)
        phone_expected = (
            call.reservation_draft.phone is None
            and call.reservation_draft.party_size is not None
            and call.reservation_draft.requested_time_text is not None
            and call.reservation_draft.customer_name is not None
        )
        quality = evaluate_transcript_quality(
            stt.transcript,
            confidence=stt.confidence,
            allow_phone_number=phone_expected,
        )
        accepted = vad.has_speech and quality.accepted

        if accepted:
            agent_result = agent.handle_turn(
                call.call_id,
                transcript=stt.transcript,
                confidence=stt.confidence or 0.95,
                observed_at=datetime.now(UTC),
            )
            reply_text = agent_result.reply_text
            agent_payload: dict[str, object] = {
                "intent": str(agent_result.intent),
                "action_name": agent_result.action_name,
                "missing_fields": list(agent_result.missing_fields),
                "reply_text": agent_result.reply_text,
                "escalated": agent_result.escalated,
                "call_status": str(agent_result.call.status),
                "reservation_draft": asdict(agent_result.call.reservation_draft),
            }
        else:
            reply_text = "No le he entendido bien. Puede repetirlo?"
            agent_payload = {
                "skipped": True,
                "reason": "vad_or_transcript_quality_blocked",
                "reply_text": reply_text,
            }

        tts_payload: dict[str, object] | None = None
        if tts_adapter is not None and reply_text:
            tts_path = args.output_dir / f"turn_{turn_number:02d}_reply.wav"
            tts_result = tts_adapter.synthesize_to_file(reply_text, tts_path)
            tts_payload = asdict(tts_result)
            if args.play:
                _play_wav(tts_path, sounddevice_module=sd)

        payload = {
            "turn": turn_number,
            "input_audio": str(wav_path),
            "vad": vad,
            "stt": stt,
            "transcript_quality": quality,
            "accepted_for_agent": accepted,
            "agent": agent_payload,
            "tts": tts_payload,
        }
        print(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2))

        if accepted and agent_payload.get("call_status") in {"confirmed", "rejected", "escalated"}:
            print("Llamada resuelta por el agente.")
            break


def _record_wav(
    path: Path,
    *,
    seconds: float,
    sample_rate: int,
    device: int | None,
    sounddevice_module: Any,
) -> None:
    recording = sounddevice_module.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device,
    )
    sounddevice_module.wait()
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(recording.tobytes())


def _play_wav(path: Path, *, sounddevice_module: Any) -> None:
    try:
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return
    except ModuleNotFoundError:
        pass
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())
    if channels != 1 or sample_width != 2:
        raise ValueError("La reproduccion local espera WAV mono PCM16.")
    samples = [
        int.from_bytes(frames[index : index + 2], "little", signed=True) / 32768
        for index in range(0, len(frames), 2)
    ]
    sounddevice_module.play(samples, sample_rate)
    sounddevice_module.wait()


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
