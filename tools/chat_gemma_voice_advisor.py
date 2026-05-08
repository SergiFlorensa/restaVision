from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from time import sleep

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.voice.background_advisor import (
        BackgroundAdviceRequest,
        build_background_voice_advisor,
    )
    from services.voice.response_compressor import DEFAULT_OLLAMA_GEMMA4_MODEL
    from services.voice.tts import DEFAULT_PIPER_CONFIG_PATH, DEFAULT_PIPER_MODEL_PATH
    from tools.synthesize_voice_reply import _play_wav

    parser = argparse.ArgumentParser(
        description="Chat local por texto para probar Gemma 4 como asesor telefonico."
    )
    parser.add_argument("--model", default=DEFAULT_OLLAMA_GEMMA4_MODEL)
    parser.add_argument("--num-thread", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=256)
    parser.add_argument("--num-predict", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=24.0)
    parser.add_argument("--wait", type=float, default=24.0)
    parser.add_argument("--play", action="store_true")
    parser.add_argument("--tts-engine", default="piper", choices=("piper", "kokoro_onnx", "mock"))
    parser.add_argument("--voice-profile", default="castilian_service")
    parser.add_argument("--voice-postprocess", default="clarity")
    args = parser.parse_args()

    from services.voice.audio_effects import postprocess_voice_wav
    from services.voice.tts import build_tts_adapter

    advisor = build_background_voice_advisor(
        "ollama",
        model=args.model,
        timeout_seconds=args.timeout,
        num_thread=args.num_thread,
        num_ctx=args.num_ctx,
        num_predict=args.num_predict,
        temperature=args.temperature,
    )
    tts_adapter = None
    if args.play:
        tts_adapter = build_tts_adapter(
            args.tts_engine,
            model_path=DEFAULT_PIPER_MODEL_PATH if args.tts_engine == "piper" else None,
            voices_path=DEFAULT_PIPER_CONFIG_PATH if args.tts_engine == "piper" else None,
            voice_profile=args.voice_profile,
            cache_dir=Path("data/local_samples/tts_cache"),
        )

    call_id = "gemma_text_chat"
    context: list[str] = []
    print("Chat Gemma 4 para RestaurIA. Escribe 'q' para salir.")
    print("Agente: Piemontesa Paseo de Prim, diga.")
    while True:
        user_text = input("\nCliente> ").strip()
        if user_text.lower() in {"q", "quit", "salir"}:
            break
        if not user_text:
            continue
        request = BackgroundAdviceRequest(
            call_id=call_id,
            transcript=user_text,
            intent="restaurant_call",
            reason="manual_text_chat",
            conversation_context=tuple(context[-6:]),
            reservation_context={},
        )
        advisor.request_advice(request)
        result = None
        for _ in range(max(1, int(args.wait / 0.2))):
            result = advisor.consume_ready(call_id)
            if result is not None:
                break
            sleep(0.2)
        if result is None:
            reply = "Lo estoy revisando. Un momento, por favor."
            payload = {"status": "timeout", "wait_seconds": args.wait}
        else:
            reply = result.reply_text or "Lo estoy revisando, un momento."
            payload = asdict(result)
        print(f"Agente: {reply}")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        context.append(f"Cliente: {user_text}")
        context.append(f"Agente: {reply}")
        if tts_adapter is not None:
            output_path = Path("data/local_samples/gemma_text_chat/last_reply.wav")
            tts_result = tts_adapter.synthesize_to_file(reply, output_path)
            postprocess_voice_wav(output_path, preset=args.voice_postprocess)
            print(json.dumps({"tts": asdict(tts_result)}, ensure_ascii=False, indent=2))
            _play_wav(output_path)


if __name__ == "__main__":
    main()
