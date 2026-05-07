from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DEFAULT_BENCHMARK_TEXTS = (
    "A que hora le gustaria la reserva?",
    (
        "Reserva confirmada para 2 personas a las 21:30, a nombre de Sergi. "
        "Muchas gracias, le esperamos en la Piemontesa de Passeig de Prim."
    ),
    (
        "No he entendido bien el telefono. Digamelo de nuevo, por favor, "
        "con los nueve digitos seguidos."
    ),
)


def main() -> None:
    from services.voice.response_compressor import (
        DEFAULT_OLLAMA_GEMMA4_MODEL,
        DEFAULT_OLLAMA_URL,
        build_voice_reply_compressor,
    )

    parser = argparse.ArgumentParser(
        description="Benchmark local de compresion de respuestas con Ollama antes del TTS."
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=[DEFAULT_OLLAMA_GEMMA4_MODEL],
        help=("Modelos de Ollama a comparar. Ejemplo: gemma4:e2b-it-q4_K_M gemma4:e4b-it-q4_K_M"),
    )
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--num-predict", type=int, default=24)
    parser.add_argument("--num-ctx", type=int, default=512)
    parser.add_argument("--num-thread", type=int, default=None)
    parser.add_argument("--keep-alive", default="30m")
    args = parser.parse_args()

    report: dict[str, object] = {
        "runs": args.runs,
        "ollama_url": args.ollama_url,
        "models": [],
    }
    model_reports: list[dict[str, object]] = []
    for model in args.models:
        compressor = build_voice_reply_compressor(
            "ollama",
            model=model,
            endpoint_url=args.ollama_url,
            timeout_seconds=args.timeout,
            keep_alive=args.keep_alive,
            num_predict=args.num_predict,
            num_ctx=args.num_ctx,
            num_thread=args.num_thread,
        )
        results = []
        for _ in range(args.runs):
            for text in DEFAULT_BENCHMARK_TEXTS:
                results.append(compressor.compress(text))
        elapsed_values = [result.elapsed_ms for result in results]
        model_reports.append(
            {
                "model": model,
                "samples": [_to_jsonable(asdict(result)) for result in results],
                "summary": {
                    "avg_elapsed_ms": round(mean(elapsed_values), 2),
                    "max_elapsed_ms": max(elapsed_values),
                    "applied_count": sum(1 for result in results if result.applied),
                    "fallback_count": sum(
                        1 for result in results if "fallback_reason" in result.metadata
                    ),
                },
            }
        )
    report["models"] = model_reports
    print(json.dumps(report, ensure_ascii=False, indent=2))


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
