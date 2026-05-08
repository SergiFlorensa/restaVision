from __future__ import annotations

import argparse
import json
import sys
import wave
from collections import deque
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.events.service import RestaurantMVPService
    from services.voice.agent import VoiceReservationAgent
    from services.voice.audio_effects import VOICE_POSTPROCESS_PRESETS
    from services.voice.audio_quality import (
        evaluate_transcript_quality,
        read_pcm16_wav,
        simple_energy_vad,
    )
    from services.voice.background_advisor import build_background_voice_advisor
    from services.voice.response_compressor import (
        DEFAULT_OLLAMA_GEMMA4_MODEL,
        DEFAULT_OLLAMA_URL,
        build_voice_reply_compressor,
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
    from tools.interactive_voice_call import _should_accept_interactive_turn

    parser = argparse.ArgumentParser(
        description="Llamada local manos libres: VAD -> STT -> agente -> TTS -> escucha."
    )
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--device", type=int, default=None)
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--max-call-seconds", type=float, default=180.0)
    parser.add_argument("--frame-ms", type=int, default=30)
    parser.add_argument("--silence-ms", type=int, default=850)
    parser.add_argument("--min-utterance-ms", type=int, default=360)
    parser.add_argument("--max-utterance-ms", type=int, default=9000)
    parser.add_argument("--pre-roll-ms", type=int, default=240)
    parser.add_argument("--energy-threshold", type=float, default=0.012)
    parser.add_argument("--calibrate-seconds", type=float, default=1.2)
    parser.add_argument("--threshold-multiplier", type=float, default=3.2)
    parser.add_argument("--output-dir", type=Path, default=Path("data/local_samples/handsfree"))
    parser.add_argument("--stt-engine", default="vosk", choices=("vosk", "mock"))
    parser.add_argument(
        "--stt-model-path",
        default="models/checkpoints/vosk-model-small-es-0.42",
    )
    parser.add_argument(
        "--tts-engine",
        default="piper",
        choices=("none", "kokoro_onnx", "piper", "windows_sapi", "mock"),
    )
    parser.add_argument("--tts-model-path", default=None)
    parser.add_argument("--tts-voices-path", default=None)
    parser.add_argument("--tts-voice", default=None)
    parser.add_argument("--tts-language", default="es")
    parser.add_argument("--tts-speed", type=float, default=1.0)
    parser.add_argument(
        "--tts-voice-profile",
        default="castilian_service",
        choices=tuple(sorted(VOICE_RENDERING_PROFILES)),
    )
    parser.add_argument(
        "--voice-postprocess",
        default="clarity",
        choices=VOICE_POSTPROCESS_PRESETS,
    )
    parser.add_argument(
        "--reply-compressor",
        default="none",
        choices=("none", "ollama"),
    )
    parser.add_argument("--reply-compressor-model", default=DEFAULT_OLLAMA_GEMMA4_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-timeout", type=float, default=6.0)
    parser.add_argument("--ollama-keep-alive", default="30m")
    parser.add_argument("--ollama-num-predict", type=int, default=24)
    parser.add_argument("--ollama-num-ctx", type=int, default=512)
    parser.add_argument("--ollama-num-thread", type=int, default=None)
    parser.add_argument(
        "--background-advisor",
        default="ollama",
        choices=("none", "ollama"),
    )
    parser.add_argument("--background-advisor-timeout", type=float, default=24.0)
    parser.add_argument("--background-advisor-wait", type=float, default=18.0)
    parser.add_argument("--background-advisor-num-predict", type=int, default=28)
    parser.add_argument("--background-advisor-num-ctx", type=int, default=256)
    parser.add_argument("--background-advisor-temperature", type=float, default=0.1)
    parser.add_argument(
        "--opening-greeting",
        default="Piemontesa Paseo de Prim, diga.",
    )
    args = parser.parse_args()

    try:
        import sounddevice as sd
    except ModuleNotFoundError as exc:
        raise SystemExit("sounddevice no esta instalado. Ejecuta requirements/audio.txt") from exc

    if args.list_devices:
        print(sd.query_devices())
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stt_adapter = build_stt_adapter(args.stt_engine, model_path=args.stt_model_path)
    reply_compressor = build_voice_reply_compressor(
        args.reply_compressor,
        model=args.reply_compressor_model,
        endpoint_url=args.ollama_url,
        timeout_seconds=args.ollama_timeout,
        keep_alive=args.ollama_keep_alive,
        num_predict=args.ollama_num_predict,
        num_ctx=args.ollama_num_ctx,
        num_thread=args.ollama_num_thread,
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
            voice_profile=args.tts_voice_profile,
            cache_dir=Path("data/local_samples/tts_cache"),
        )
    background_advisor = build_background_voice_advisor(
        args.background_advisor,
        model=args.reply_compressor_model,
        endpoint_url=args.ollama_url,
        timeout_seconds=args.background_advisor_timeout,
        num_thread=args.ollama_num_thread,
        num_predict=args.background_advisor_num_predict,
        num_ctx=args.background_advisor_num_ctx,
        temperature=args.background_advisor_temperature,
    )
    agent = VoiceReservationAgent(
        RestaurantMVPService(),
        background_advisor=background_advisor,
    )
    call = agent.start_call(source_channel="local_handsfree_microphone")

    if tts_adapter is not None and args.opening_greeting.strip():
        _speak_reply(
            args.opening_greeting,
            args.output_dir / "turn_00_opening.wav",
            tts_adapter=tts_adapter,
            reply_compressor=reply_compressor,
            voice_postprocess=args.voice_postprocess,
            sounddevice_module=sd,
        )
    print(f"Llamada manos libres iniciada: {call.call_id}")
    print("Habla cuando quieras. Ctrl+C para salir.")
    threshold = _calibrate_threshold(
        sounddevice_module=sd,
        seconds=args.calibrate_seconds,
        sample_rate=args.sample_rate,
        device=args.device,
        frame_ms=args.frame_ms,
        absolute_threshold=args.energy_threshold,
        threshold_multiplier=args.threshold_multiplier,
    )
    print(json.dumps({"vad_threshold": round(threshold, 6)}, ensure_ascii=False))

    started_call = monotonic()
    for turn_number in range(1, args.max_turns + 1):
        if monotonic() - started_call > args.max_call_seconds:
            print("Tiempo maximo de llamada alcanzado.")
            break
        print(f"\nEscuchando turno {turn_number}/{args.max_turns}...")
        wav_path = args.output_dir / f"turn_{turn_number:02d}_input.wav"
        endpoint = _record_until_endpoint(
            wav_path,
            sounddevice_module=sd,
            sample_rate=args.sample_rate,
            device=args.device,
            frame_ms=args.frame_ms,
            threshold=threshold,
            silence_ms=args.silence_ms,
            min_utterance_ms=args.min_utterance_ms,
            max_utterance_ms=args.max_utterance_ms,
            pre_roll_ms=args.pre_roll_ms,
        )
        if endpoint["reason"] == "timeout_no_speech":
            print(json.dumps(endpoint, ensure_ascii=False))
            continue

        read_result = read_pcm16_wav(wav_path)
        vad = simple_energy_vad(
            read_result.audio,
            read_result.samples,
            absolute_threshold=threshold,
            min_speech_ms=max(180, min(args.min_utterance_ms, 350)),
        )
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
        accepted = _should_accept_interactive_turn(vad=vad, quality=quality, call=call)
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
                "reply_text": reply_text,
                "escalated": agent_result.escalated,
                "call_status": str(agent_result.call.status),
                "reservation_draft": asdict(agent_result.call.reservation_draft),
            }
        else:
            reply_text = "Disculpe, no le he entendido bien. Puede repetirlo?"
            agent_payload = {"skipped": True, "reason": "vad_or_quality_blocked"}

        reply_tts = None
        if tts_adapter is not None:
            reply_tts = _speak_reply(
                reply_text,
                args.output_dir / f"turn_{turn_number:02d}_reply.wav",
                tts_adapter=tts_adapter,
                reply_compressor=reply_compressor,
                voice_postprocess=args.voice_postprocess,
                sounddevice_module=sd,
            )
        payload = {
            "turn": turn_number,
            "endpoint": endpoint,
            "vad": vad,
            "stt": stt,
            "transcript_quality": quality,
            "accepted_for_agent": accepted,
            "agent": agent_payload,
            "tts": reply_tts,
        }
        print(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2))

        if accepted and agent_payload.get("action_name") == "utter_background_advice_bridge":
            follow_up = _wait_for_background_reply(
                agent,
                call.call_id,
                timeout_seconds=args.background_advisor_wait,
            )
            if follow_up is not None and tts_adapter is not None:
                follow_up_tts = _speak_reply(
                    follow_up.reply_text,
                    args.output_dir / f"turn_{turn_number:02d}_background.wav",
                    tts_adapter=tts_adapter,
                    reply_compressor=reply_compressor,
                    voice_postprocess=args.voice_postprocess,
                    sounddevice_module=sd,
                )
                print(
                    json.dumps(
                        _to_jsonable(
                            {
                                "turn": turn_number,
                                "background_advisor": {
                                    "reply_text": follow_up.reply_text,
                                    "action_payload": follow_up.action_payload,
                                },
                                "tts": follow_up_tts,
                            }
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                )

        if accepted and agent_payload.get("call_status") in {"confirmed", "rejected", "escalated"}:
            print("Llamada resuelta por el agente.")
            break


def _calibrate_threshold(
    *,
    sounddevice_module: Any,
    seconds: float,
    sample_rate: int,
    device: int | None,
    frame_ms: int,
    absolute_threshold: float,
    threshold_multiplier: float,
) -> float:
    if seconds <= 0:
        return absolute_threshold
    print(f"Calibrando ruido ambiente {seconds:.1f}s. Mantén silencio...")
    frames = _record_frames(
        sounddevice_module=sounddevice_module,
        seconds=seconds,
        sample_rate=sample_rate,
        device=device,
    )
    rms_values = _frame_rms_values(frames, sample_rate=sample_rate, frame_ms=frame_ms)
    noise_floor = sorted(rms_values)[len(rms_values) // 2] if rms_values else 0.0
    return max(absolute_threshold, noise_floor * threshold_multiplier)


def _record_until_endpoint(
    path: Path,
    *,
    sounddevice_module: Any,
    sample_rate: int,
    device: int | None,
    frame_ms: int,
    threshold: float,
    silence_ms: int,
    min_utterance_ms: int,
    max_utterance_ms: int,
    pre_roll_ms: int,
) -> dict[str, object]:
    frame_count = max(1, int(sample_rate * frame_ms / 1000))
    pre_roll_frames = max(1, int(pre_roll_ms / frame_ms))
    max_frames = max(1, int(max_utterance_ms / frame_ms))
    silence_frames_needed = max(1, int(silence_ms / frame_ms))
    min_frames = max(1, int(min_utterance_ms / frame_ms))
    pre_roll: deque[bytes] = deque(maxlen=pre_roll_frames)
    utterance: list[bytes] = []
    speech_started = False
    silence_frames = 0
    speech_frames = 0
    total_frames = 0
    listen_deadline = monotonic() + 30.0

    while True:
        chunk = sounddevice_module.rec(
            frame_count,
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device,
        )
        sounddevice_module.wait()
        raw = chunk.tobytes()
        rms = _pcm16_rms(raw)
        is_speech = rms >= threshold
        total_frames += 1
        if not speech_started:
            pre_roll.append(raw)
            if is_speech:
                speech_started = True
                utterance.extend(pre_roll)
                speech_frames += 1
            elif monotonic() > listen_deadline:
                return {"reason": "timeout_no_speech", "threshold": round(threshold, 6)}
            continue

        utterance.append(raw)
        if is_speech:
            speech_frames += 1
            silence_frames = 0
        else:
            silence_frames += 1
        if len(utterance) >= max_frames:
            reason = "max_utterance_ms"
            break
        if len(utterance) >= min_frames and silence_frames >= silence_frames_needed:
            reason = "end_silence"
            break

    _write_raw_pcm16_wav(path, utterance, sample_rate=sample_rate)
    return {
        "reason": reason,
        "path": str(path),
        "duration_ms": len(utterance) * frame_ms,
        "speech_ms_estimate": speech_frames * frame_ms,
        "total_frames_seen": total_frames,
        "threshold": round(threshold, 6),
    }


def _record_frames(
    *,
    sounddevice_module: Any,
    seconds: float,
    sample_rate: int,
    device: int | None,
) -> bytes:
    recording = sounddevice_module.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device,
    )
    sounddevice_module.wait()
    return recording.tobytes()


def _frame_rms_values(raw: bytes, *, sample_rate: int, frame_ms: int) -> list[float]:
    frame_bytes = max(2, int(sample_rate * frame_ms / 1000) * 2)
    return [
        _pcm16_rms(raw[index : index + frame_bytes]) for index in range(0, len(raw), frame_bytes)
    ]


def _pcm16_rms(raw: bytes) -> float:
    if len(raw) < 2:
        return 0.0
    total = 0.0
    count = 0
    for index in range(0, len(raw) - 1, 2):
        value = int.from_bytes(raw[index : index + 2], "little", signed=True) / 32768.0
        total += value * value
        count += 1
    return (total / count) ** 0.5 if count else 0.0


def _write_raw_pcm16_wav(path: Path, frames: list[bytes], *, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))


def _speak_reply(
    text: str,
    path: Path,
    *,
    tts_adapter: Any,
    reply_compressor: Any,
    voice_postprocess: str,
    sounddevice_module: Any,
) -> dict[str, object]:
    from services.voice.audio_effects import postprocess_voice_wav
    from tools.interactive_voice_call import _play_wav

    compression = reply_compressor.compress(text)
    tts = tts_adapter.synthesize_to_file(compression.output_text, path)
    postprocess = postprocess_voice_wav(path, preset=voice_postprocess)
    _play_wav(path, sounddevice_module=sounddevice_module)
    return {
        "compression": asdict(compression),
        "tts": asdict(tts),
        "voice_postprocess": asdict(postprocess),
    }


def _wait_for_background_reply(
    agent: Any,
    call_id: str,
    *,
    timeout_seconds: float,
) -> Any | None:
    deadline = monotonic() + max(0.0, timeout_seconds)
    while monotonic() < deadline:
        result = agent.consume_background_reply(call_id)
        if result is not None:
            return result
        sleep(0.25)
    return None


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
