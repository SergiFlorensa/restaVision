from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from time import perf_counter, sleep
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


DEFAULT_MODEL = "gemma4:e2b-it-q4_K_M"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_PROMPTS = (
    (
        "window_request",
        "Cliente: Quiero reservar mesa cerca de la ventana porque viene una persona mayor. "
        "Intencion: create_reservation. Respuesta telefonica breve:",
    ),
    (
        "late_arrival",
        "Cliente: Llegaremos diez minutos tarde a la reserva de Juanito. "
        "Intencion: create_reservation. Respuesta telefonica breve:",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepara y mide Gemma/Ollama para el asesor de voz local. "
            "Pensado para portatil CPU con poca RAM libre."
        )
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=float, default=18.0)
    parser.add_argument("--num-thread", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=256)
    parser.add_argument("--num-predict", type=int, default=28)
    parser.add_argument("--keep-alive", default="30m")
    parser.add_argument(
        "--stop-loaded",
        action="store_true",
        help="Ejecuta 'ollama stop' sobre modelos cargados distintos al modelo objetivo.",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=1.5,
        help="Pausa tras parar modelos para que el SO recupere memoria.",
    )
    args = parser.parse_args()

    report: dict[str, Any] = {
        "model": args.model,
        "loaded_before": _ollama_ps(),
        "stopped": [],
        "settings": {
            "timeout": args.timeout,
            "num_thread": args.num_thread,
            "num_ctx": args.num_ctx,
            "num_predict": args.num_predict,
            "keep_alive": args.keep_alive,
        },
        "probes": [],
    }

    if args.stop_loaded:
        for loaded_model in _loaded_model_names(report["loaded_before"]):
            if loaded_model != args.model:
                stop_result = _run_ollama_stop(loaded_model)
                report["stopped"].append(stop_result)
        if report["stopped"]:
            sleep(max(0.0, args.cooldown_seconds))
        report["loaded_after_stop"] = _ollama_ps()

    warmup = _probe(
        model=args.model,
        endpoint_url=args.ollama_url,
        prompt="Responde solo: listo.",
        timeout=args.timeout,
        num_thread=args.num_thread,
        num_ctx=args.num_ctx,
        num_predict=4,
        keep_alive=args.keep_alive,
    )
    report["warmup"] = warmup

    for name, prompt in DEFAULT_PROMPTS:
        probe = _probe(
            model=args.model,
            endpoint_url=args.ollama_url,
            prompt=prompt,
            timeout=args.timeout,
            num_thread=args.num_thread,
            num_ctx=args.num_ctx,
            num_predict=args.num_predict,
            keep_alive=args.keep_alive,
        )
        probe["name"] = name
        report["probes"].append(probe)

    report["loaded_after"] = _ollama_ps()
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _ollama_ps() -> str:
    try:
        completed = subprocess.run(
            ["ollama", "ps"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"ollama ps failed: {type(exc).__name__}: {exc}"
    return completed.stdout.strip() or completed.stderr.strip()


def _loaded_model_names(ps_output: str) -> list[str]:
    names: list[str] = []
    for line in ps_output.splitlines()[1:]:
        columns = line.split()
        if columns:
            names.append(columns[0])
    return names


def _run_ollama_stop(model: str) -> dict[str, Any]:
    started = perf_counter()
    completed = subprocess.run(
        ["ollama", "stop", model],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "model": model,
        "returncode": completed.returncode,
        "elapsed_ms": int(round((perf_counter() - started) * 1000)),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _probe(
    *,
    model: str,
    endpoint_url: str,
    prompt: str,
    timeout: float,
    num_thread: int,
    num_ctx: int,
    num_predict: int,
    keep_alive: str,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "think": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 20,
            "num_thread": num_thread,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "stop": ["\n"],
        },
        "keep_alive": keep_alive,
    }
    started = perf_counter()
    first_token_ms: int | None = None
    first_sentence_ms: int | None = None
    collected = ""
    request = urllib.request.Request(
        endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                if not raw_line:
                    continue
                line = json.loads(raw_line.decode("utf-8"))
                token = line.get("response")
                if isinstance(token, str) and token:
                    if first_token_ms is None:
                        first_token_ms = int(round((perf_counter() - started) * 1000))
                    collected += token
                    if first_sentence_ms is None and any(mark in collected for mark in ".!?"):
                        first_sentence_ms = int(round((perf_counter() - started) * 1000))
                if line.get("done") is True:
                    break
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "error_type": "HTTPError",
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace")[:500],
            "total_ms": int(round((perf_counter() - started) * 1000)),
        }
    except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "total_ms": int(round((perf_counter() - started) * 1000)),
        }
    return {
        "ok": True,
        "first_token_ms": first_token_ms,
        "first_sentence_ms": first_sentence_ms,
        "total_ms": int(round((perf_counter() - started) * 1000)),
        "text": collected.strip(),
    }


if __name__ == "__main__":
    main()
