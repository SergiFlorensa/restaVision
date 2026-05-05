from __future__ import annotations

import json
from pathlib import Path

from services.voice.stt_manifest import load_stt_manifest, validate_stt_manifest


def test_load_stt_manifest_json_with_slots(tmp_path: Path) -> None:
    wav_path = tmp_path / "reserva.wav"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "case_id": "reserva",
                    "wav_path": str(wav_path),
                    "expected_transcript": "Reserva para 2",
                    "expected_intent": "create_reservation",
                    "expected_slots": {"party_size": 2},
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_stt_manifest(manifest_path)

    assert len(cases) == 1
    assert cases[0].case_id == "reserva"
    assert cases[0].expected_slots == {"party_size": 2}


def test_validate_stt_manifest_reports_missing_wav(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps([{"case_id": "missing", "wav_path": str(tmp_path / "missing.wav")}]),
        encoding="utf-8",
    )

    report = validate_stt_manifest(manifest_path)

    assert report.valid is False
    assert report.issues[0].field == "wav_path"


def test_validate_stt_manifest_allows_template_without_wav(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps([{"case_id": "template", "wav_path": "data/local_samples/template.wav"}]),
        encoding="utf-8",
    )

    report = validate_stt_manifest(manifest_path, require_existing_wavs=False)

    assert report.valid is True
    assert report.case_count == 1
