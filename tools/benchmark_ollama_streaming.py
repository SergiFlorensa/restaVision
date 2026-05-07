from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from time import perf_counter

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.voice.response_compressor import DEFAULT_OLLAMA_GEMMA4_MODEL, DEFAULT_OLLAMA_URL

    parser = argparse.ArgumentParser(
        description="Benchmark Python equivalente al probe C++ de streaming Ollama."
    )
    parser.add_argument("--model", default=DEFAULT_OLLAMA_GEMMA4_MODEL)
    parser.add_argument("--url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--prompt",
        default=(
            "Cliente: Quiero una mesa cerca de la ventana porque viene una persona mayor. "
            "Respuesta telefonica breve:"
        ),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--num-thread", type=int, default=None)
    parser.add_argument("--num-predict", type=int, default=48)
    parser.add_argument("--num-ctx", type=int, default=768)
    args = parser.parse_args()

    options: dict[str, object] = {
        "num_predict": args.num_predict,
        "num_ctx": args.num_ctx,
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 20,
    }
    if args.num_thread is not None:
        options["num_thread"] = args.num_thread
    payload = {
        "model": args.model,
        "stream": True,
        "think": False,
        "keep_alive": "30m",
        "system": "Responde como agente telefonico de restaurante. Maximo 25 palabras.",
        "prompt": args.prompt,
        "options": options,
    }
    started = perf_counter()
    request = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    first_response_marker_ms: int | None = None
    first_period_seen_ms: int | None = None
    collected = ""
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            for raw_line in response:
                if not raw_line:
                    continue
                line = json.loads(raw_line.decode("utf-8"))
                token = line.get("response")
                if isinstance(token, str):
                    if first_response_marker_ms is None:
                        first_response_marker_ms = _elapsed_ms(started)
                    collected += token
                    if first_period_seen_ms is None and "." in collected:
                        first_period_seen_ms = _elapsed_ms(started)
                        break
                if line.get("done") is True:
                    break
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "model": args.model,
                    "error": f"HTTP {exc.code}",
                    "body": error_body[:500],
                    "total_probe_ms": _elapsed_ms(started),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(
        json.dumps(
            {
                "model": args.model,
                "first_response_marker_ms": first_response_marker_ms,
                "first_period_seen_ms": first_period_seen_ms,
                "total_probe_ms": _elapsed_ms(started),
                "collected": collected.strip(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))


if __name__ == "__main__":
    main()
