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
        "--voice-postprocess",
        default="none",
        choices=VOICE_POSTPROCESS_PRESETS,
        help="Postprocesado Rust para salida TTS: clarity, warm o phone.",
    )
    parser.add_argument(
        "--voice-postprocessor-path",
        default=None,
        help="Ruta opcional al binario Rust de postprocesado de voz.",
    )
    parser.add_argument(
        "--reply-compressor",
        default="none",
        choices=("none", "ollama"),
        help="Reescribe la respuesta antes del TTS. Ollama usa un modelo local.",
    )
    parser.add_argument(
        "--reply-compressor-model",
        default=DEFAULT_OLLAMA_GEMMA4_MODEL,
        help="Modelo local de Ollama para compresion, por ejemplo gemma4:e2b-it-q4_K_M.",
    )
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-timeout", type=float, default=6.0)
    parser.add_argument("--ollama-keep-alive", default="30m")
    parser.add_argument("--ollama-num-predict", type=int, default=24)
    parser.add_argument("--ollama-num-ctx", type=int, default=512)
    parser.add_argument("--ollama-num-thread", type=int, default=None)
    parser.add_argument(
        "--background-advisor",
        default="none",
        choices=("none", "ollama"),
        help="Usa Gemma/Ollama en segundo plano para peticiones complejas.",
    )
    parser.add_argument("--background-advisor-timeout", type=float, default=20.0)
    parser.add_argument("--background-advisor-wait", type=float, default=14.0)
    parser.add_argument(
        "--background-advisor-num-predict",
        type=int,
        default=28,
        help="Limite de tokens del asesor de fondo. Bajo para Gemma en CPU.",
    )
    parser.add_argument(
        "--background-advisor-num-ctx",
        type=int,
        default=256,
        help="Contexto del asesor de fondo. 256 reduce memoria para Gemma local.",
    )
    parser.add_argument(
        "--background-advisor-temperature",
        type=float,
        default=0.15,
        help="Temperatura del asesor de fondo. Baja para evitar invenciones.",
    )
    parser.add_argument(
        "--no-background-advisor-stream",
        action="store_true",
        help="Espera a la respuesta completa de Ollama en vez de cortar la primera frase util.",
    )
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
            style=args.tts_style,
            voice_profile=args.tts_voice_profile,
            cache_dir=None if args.no_tts_cache else args.tts_cache_dir,
        )

    background_advisor = build_background_voice_advisor(
        args.background_advisor,
        model=args.reply_compressor_model,
        endpoint_url=args.ollama_url,
        timeout_seconds=args.background_advisor_timeout,
        num_thread=args.ollama_num_thread,
        num_predict=args.background_advisor_num_predict,
        num_ctx=args.background_advisor_num_ctx,
        keep_alive=args.ollama_keep_alive,
        temperature=args.background_advisor_temperature,
        stream_early_stop=not args.no_background_advisor_stream,
    )
    agent = VoiceReservationAgent(
        RestaurantMVPService(),
        background_advisor=background_advisor,
    )
    call = agent.start_call(source_channel="local_interactive_microphone")
    print(f"Llamada local iniciada: {call.call_id}")
    if tts_adapter is not None and args.opening_greeting.strip() and not args.skip_opening_greeting:
        _precache_critical_replies(tts_adapter, args.output_dir)
        greeting_path = args.output_dir / "turn_00_opening_greeting.wav"
        greeting_tts = tts_adapter.synthesize_to_file(args.opening_greeting, greeting_path)
        greeting_postprocess = _postprocess_reply_audio(
            greeting_path,
            preset=args.voice_postprocess,
            processor_path=args.voice_postprocessor_path,
        )
        print(f"Agente: {greeting_tts.text}")
        if greeting_postprocess.applied:
            print(json.dumps({"opening_voice_postprocess": asdict(greeting_postprocess)}))
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
        accepted = _should_accept_interactive_turn(
            vad=vad,
            quality=quality,
            call=call,
        )

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
        compression_payload: dict[str, object] | None = None
        if tts_adapter is not None and reply_text:
            tts_path = args.output_dir / f"turn_{turn_number:02d}_reply.wav"
            compression_result = reply_compressor.compress(reply_text)
            compression_payload = asdict(compression_result)
            tts_result = tts_adapter.synthesize_to_file(compression_result.output_text, tts_path)
            postprocess_result = _postprocess_reply_audio(
                tts_path,
                preset=args.voice_postprocess,
                processor_path=args.voice_postprocessor_path,
            )
            tts_payload = asdict(tts_result)
            tts_payload["voice_postprocess"] = asdict(postprocess_result)
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
            "reply_compression": compression_payload,
            "tts": tts_payload,
        }
        print(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2))

        if accepted and agent_payload.get("call_status") in {"confirmed", "rejected", "escalated"}:
            print("Llamada resuelta por el agente.")
            break

        if (
            accepted
            and agent_payload.get("action_name") == "utter_background_advice_bridge"
            and tts_adapter is not None
        ):
            follow_up = _wait_for_background_reply(
                agent,
                call.call_id,
                timeout_seconds=args.background_advisor_wait,
            )
            if follow_up is not None:
                follow_up_path = args.output_dir / f"turn_{turn_number:02d}_background_reply.wav"
                follow_up_tts = tts_adapter.synthesize_to_file(
                    follow_up.reply_text,
                    follow_up_path,
                )
                follow_up_postprocess = _postprocess_reply_audio(
                    follow_up_path,
                    preset=args.voice_postprocess,
                    processor_path=args.voice_postprocessor_path,
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
                                "tts": asdict(follow_up_tts),
                                "voice_postprocess": asdict(follow_up_postprocess),
                            }
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                if args.play:
                    _play_wav(follow_up_path, sounddevice_module=sd)


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


def _wait_for_background_reply(
    agent: Any,
    call_id: str,
    *,
    timeout_seconds: float,
) -> Any | None:
    from time import monotonic, sleep

    deadline = monotonic() + max(0.0, timeout_seconds)
    while monotonic() < deadline:
        result = agent.consume_background_reply(call_id)
        if result is not None:
            return result
        sleep(0.25)
    return None


def _postprocess_reply_audio(
    path: Path,
    *,
    preset: str,
    processor_path: str | None,
) -> Any:
    from services.voice.audio_effects import postprocess_voice_wav

    return postprocess_voice_wav(
        path,
        preset=preset,
        processor_path=processor_path,
    )


def _is_short_conversation_reply(normalized_text: str) -> bool:
    return normalized_text in {
        "si",
        "si correcto",
        "correcto",
        "perfecto",
        "vale",
        "de acuerdo",
        "ok",
        "no",
        "no correcto",
        "cancelar",
    }


def _should_accept_interactive_turn(*, vad: Any, quality: Any, call: Any) -> bool:
    normalized_text = quality.normalized_text
    if vad.has_speech and quality.accepted:
        return True
    if _is_short_conversation_reply(normalized_text):
        return vad.speech_ms >= 120 or vad.peak >= 0.035
    expected_fields = _expected_reservation_fields(call)
    if "customer_name" in expected_fields and 1 <= quality.token_count <= 4 and vad.peak >= 0.035:
        return True
    if not quality.accepted:
        return False
    if vad.speech_ms < 180 and vad.peak < 0.04:
        return False
    if "requested_time_text" in expected_fields and _looks_like_time_reply(normalized_text):
        return True
    if "party_size" in expected_fields and _looks_like_party_size_reply(normalized_text):
        return True
    if "customer_name" in expected_fields and 1 <= quality.token_count <= 4:
        return True
    if "phone" in expected_fields and _looks_like_phone_reply(normalized_text):
        return True
    return False


def _expected_reservation_fields(call: Any) -> set[str]:
    draft = call.reservation_draft
    expected: set[str] = set()
    if draft.party_size is None:
        expected.add("party_size")
    if draft.requested_time_text is None:
        expected.add("requested_time_text")
    if draft.customer_name is None:
        expected.add("customer_name")
    if draft.phone is None:
        expected.add("phone")
    return expected


def _looks_like_time_reply(normalized_text: str) -> bool:
    tokens = set(normalized_text.split())
    return bool(
        tokens.intersection(
            {
                "hora",
                "horas",
                "manana",
                "tarde",
                "noche",
                "mediodia",
                "medio",
                "media",
                "cuarto",
            }
        )
        or "a las" in normalized_text
        or any(token.isdigit() and 0 <= int(token) <= 23 for token in tokens)
    )


def _looks_like_party_size_reply(normalized_text: str) -> bool:
    return any(token.isdigit() and 1 <= int(token) <= 20 for token in normalized_text.split())


def _looks_like_phone_reply(normalized_text: str) -> bool:
    digits = "".join(token for token in normalized_text.split() if token.isdigit())
    return len(digits) >= 6 or "telefono" in normalized_text


def _precache_critical_replies(tts_adapter: Any, output_dir: Path) -> None:
    critical_replies = {
        "precache_opening.wav": "Piemontesa Paseo de Prim, diga.",
        "precache_bridge.wav": (
            "Entiendo. Lo compruebo un momento. "
            "Si quiere consultar la carta u otra informacion del restaurante, "
            "puede entrar en la web de La Piemontesa."
        ),
        "precache_repair.wav": "No le he entendido bien. Puede repetirlo?",
        "precache_time.wav": "A que hora le gustaria la reserva?",
        "precache_phone.wav": "Me confirma un numero de telefono de contacto?",
    }
    for filename, text in critical_replies.items():
        tts_adapter.synthesize_to_file(text, output_dir / filename)


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
