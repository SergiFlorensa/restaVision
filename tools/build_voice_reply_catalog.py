from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

SAMPLE_SLOT_VALUES = {
    "customer_name": "Sergi",
    "party_size": 2,
    "spoken_time": "a las 21:30",
}


def main() -> None:
    from services.voice.reply_catalog import (
        VOICE_REPLY_TEMPLATES,
        export_voice_reply_catalog,
        render_voice_reply,
    )
    from services.voice.response_compressor import (
        DEFAULT_OLLAMA_GEMMA4_MODEL,
        DEFAULT_OLLAMA_URL,
        build_voice_reply_compressor,
    )

    parser = argparse.ArgumentParser(
        description=(
            "Exporta el catalogo de respuestas del agente y, opcionalmente, "
            "genera variantes offline con Ollama/Gemma."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/voice_reply_catalog.generated.json"),
    )
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_GEMMA4_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--num-thread", type=int, default=None)
    args = parser.parse_args()

    compressor = None
    if args.use_ollama:
        compressor = build_voice_reply_compressor(
            "ollama",
            model=args.model,
            endpoint_url=args.ollama_url,
            timeout_seconds=args.timeout,
            enable_fast_path=False,
            num_predict=32,
            num_ctx=512,
            num_thread=args.num_thread,
        )

    entries = []
    for action_name, template in VOICE_REPLY_TEMPLATES.items():
        sample_slots = {
            slot_name: SAMPLE_SLOT_VALUES[slot_name]
            for slot_name in template.slot_names
            if slot_name in SAMPLE_SLOT_VALUES
        }
        sample_text = render_voice_reply(action_name, **sample_slots)
        variants: list[dict[str, object]] = []
        if compressor is not None:
            result = compressor.compress(sample_text)
            variants.append(
                {
                    "source": "ollama",
                    "model": result.model,
                    "text": result.output_text,
                    "applied": result.applied,
                    "elapsed_ms": result.elapsed_ms,
                    "metadata": result.metadata,
                }
            )
        entries.append(
            {
                "action_name": action_name,
                "intent": template.intent,
                "template": template.template,
                "slot_names": list(template.slot_names),
                "tts_style": template.tts_style,
                "latency_tier": template.latency_tier,
                "notes": template.notes,
                "sample_text": sample_text,
                "variants": variants,
            }
        )

    payload = {
        "catalog": export_voice_reply_catalog(),
        "entries": entries,
        "generation": {
            "used_ollama": args.use_ollama,
            "model": args.model if args.use_ollama else None,
            "note": (
                "Archivo generado para analisis offline. No versionar si contiene "
                "variantes experimentales."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "entries": len(entries),
                "read_utf8_powershell": (f"Get-Content {args.output} -Encoding utf8"),
            },
            ensure_ascii=False,
        )
    )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    main()
