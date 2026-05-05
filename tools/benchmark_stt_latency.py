from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.voice.stt import build_stt_adapter
    from services.voice.stt_benchmark import run_stt_benchmark
    from services.voice.stt_manifest import validate_stt_manifest

    parser = argparse.ArgumentParser(
        description="Benchmark local de STT + quality gate + agente de voz."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--engine", default="mock", choices=("mock", "vosk", "whisper.cpp"))
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--executable-path", default=None)
    parser.add_argument("--language", default="es")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    validation = validate_stt_manifest(args.manifest, require_existing_wavs=True)
    if not validation.valid:
        print(json.dumps(_to_jsonable(validation), ensure_ascii=False, indent=2))
        raise SystemExit(2)
    cases = validation.cases
    adapter = build_stt_adapter(
        args.engine,
        model_path=args.model_path,
        executable_path=args.executable_path,
        language=args.language,
        mock_transcripts={
            Path(case.wav_path).name: case.expected_transcript or "" for case in cases
        },
    )
    report = run_stt_benchmark(cases, adapter)
    payload = _to_jsonable(report)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


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
