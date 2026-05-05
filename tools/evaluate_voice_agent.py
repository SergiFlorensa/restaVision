from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> None:
    from services.voice.evaluation import evaluate_voice_agent_baseline

    parser = argparse.ArgumentParser(
        description="Evalua el corpus baseline del agente de voz de RestaurIA."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Ruta opcional para guardar el reporte JSON.",
    )
    args = parser.parse_args()

    report = evaluate_voice_agent_baseline()
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
    if isinstance(value, Enum):
        return value.value
    return value


if __name__ == "__main__":
    main()
