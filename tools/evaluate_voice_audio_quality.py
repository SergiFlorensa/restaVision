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
    from services.voice.audio_quality import (
        evaluate_transcript_quality,
        read_pcm16_wav,
        simple_energy_vad,
    )

    parser = argparse.ArgumentParser(
        description="Evalua calidad local de un WAV antes de enviarlo al agente de voz."
    )
    parser.add_argument("wav_path", type=Path)
    parser.add_argument("--transcript", default=None)
    parser.add_argument("--reference", default=None)
    parser.add_argument("--confidence", type=float, default=None)
    args = parser.parse_args()

    read_result = read_pcm16_wav(args.wav_path)
    vad = simple_energy_vad(read_result.audio, read_result.samples)
    transcript_quality = (
        evaluate_transcript_quality(
            args.transcript,
            confidence=args.confidence,
            reference_text=args.reference,
        )
        if args.transcript is not None
        else None
    )
    payload = {
        "audio": read_result.audio,
        "vad": vad,
        "transcript_quality": transcript_quality,
        "accepted_for_agent": vad.has_speech
        and (transcript_quality is None or transcript_quality.accepted),
    }
    print(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2))


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
