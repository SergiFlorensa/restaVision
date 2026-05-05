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
    from services.voice.stt_manifest import validate_stt_manifest

    parser = argparse.ArgumentParser(description="Valida un manifest de audios STT local.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--allow-missing-wavs",
        action="store_true",
        help="Permite validar plantillas sin que existan todavia los WAV.",
    )
    args = parser.parse_args()

    report = validate_stt_manifest(
        args.manifest,
        require_existing_wavs=not args.allow_missing_wavs,
    )
    print(json.dumps(_to_jsonable(report), ensure_ascii=False, indent=2))
    if not report.valid:
        raise SystemExit(2)


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
