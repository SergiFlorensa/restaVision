from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from services.voice.stt_benchmark import SttBenchmarkCase


@dataclass(frozen=True, slots=True)
class SttManifestValidationIssue:
    case_id: str
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class SttManifestValidationReport:
    manifest_path: str
    case_count: int
    valid: bool
    issues: tuple[SttManifestValidationIssue, ...]
    cases: tuple[SttBenchmarkCase, ...]


def load_stt_manifest(path: str | Path) -> tuple[SttBenchmarkCase, ...]:
    manifest_path = Path(path)
    if manifest_path.suffix.lower() == ".json":
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON manifest must contain a list of cases.")
        return tuple(_case_from_mapping(item) for item in data)
    if manifest_path.suffix.lower() == ".csv":
        with manifest_path.open("r", encoding="utf-8", newline="") as handle:
            return tuple(_case_from_mapping(row) for row in csv.DictReader(handle))
    raise ValueError("Manifest must be .json or .csv")


def validate_stt_manifest(
    path: str | Path,
    *,
    require_existing_wavs: bool = True,
) -> SttManifestValidationReport:
    manifest_path = Path(path)
    issues: list[SttManifestValidationIssue] = []
    try:
        cases = load_stt_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 - validation should report malformed files.
        return SttManifestValidationReport(
            manifest_path=str(manifest_path),
            case_count=0,
            valid=False,
            issues=(
                SttManifestValidationIssue(
                    case_id="manifest",
                    field="file",
                    message=str(exc),
                ),
            ),
            cases=(),
        )

    seen_ids: set[str] = set()
    for case in cases:
        if not case.case_id.strip():
            issues.append(_issue(case.case_id, "case_id", "case_id is required."))
        if case.case_id in seen_ids:
            issues.append(_issue(case.case_id, "case_id", "case_id must be unique."))
        seen_ids.add(case.case_id)
        if not case.wav_path.strip():
            issues.append(_issue(case.case_id, "wav_path", "wav_path is required."))
        elif require_existing_wavs and not Path(case.wav_path).exists():
            issues.append(_issue(case.case_id, "wav_path", "WAV file does not exist."))
        if case.expected_transcript is not None and not case.expected_transcript.strip():
            issues.append(
                _issue(
                    case.case_id,
                    "expected_transcript",
                    "expected_transcript cannot be empty when provided.",
                )
            )
        if case.expected_slots is not None and not isinstance(case.expected_slots, dict):
            issues.append(
                _issue(case.case_id, "expected_slots", "expected_slots must be an object.")
            )

    return SttManifestValidationReport(
        manifest_path=str(manifest_path),
        case_count=len(cases),
        valid=not issues,
        issues=tuple(issues),
        cases=cases,
    )


def _case_from_mapping(item: object) -> SttBenchmarkCase:
    if not isinstance(item, dict):
        raise ValueError("Each manifest case must be an object.")
    expected_slots = item.get("expected_slots")
    if isinstance(expected_slots, str):
        expected_slots = json.loads(expected_slots) if expected_slots.strip() else None
    return SttBenchmarkCase(
        case_id=str(item.get("case_id", "")),
        wav_path=str(item.get("wav_path", "")),
        expected_transcript=_optional_str(item.get("expected_transcript")),
        expected_intent=_optional_str(item.get("expected_intent")),
        expected_action_name=_optional_str(item.get("expected_action_name")),
        expected_slots=expected_slots,
        confidence_override=(
            float(item["confidence_override"])
            if item.get("confidence_override") not in {None, ""}
            else None
        ),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _issue(case_id: str, field: str, message: str) -> SttManifestValidationIssue:
    return SttManifestValidationIssue(case_id=case_id or "unknown", field=field, message=message)
