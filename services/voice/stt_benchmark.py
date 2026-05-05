from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

from services.events.service import RestaurantMVPService
from services.voice.agent import VoiceReservationAgent
from services.voice.audio_quality import (
    TranscriptQualityResult,
    VadResult,
    evaluate_transcript_quality,
    read_pcm16_wav,
    simple_energy_vad,
    word_error_rate,
)
from services.voice.stt import SpeechToTextAdapter, TranscriptionResult


@dataclass(frozen=True, slots=True)
class SttBenchmarkCase:
    case_id: str
    wav_path: str
    expected_transcript: str | None = None
    expected_intent: str | None = None
    expected_action_name: str | None = None
    expected_slots: dict[str, object] | None = None
    confidence_override: float | None = None


@dataclass(frozen=True, slots=True)
class SttBenchmarkCaseResult:
    case_id: str
    wav_path: str
    audio_duration_ms: int
    stt_engine: str
    stt_model: str | None
    stt_processing_ms: int
    realtime_factor: float
    transcript: str
    wer: float | None
    vad: VadResult
    transcript_quality: TranscriptQualityResult
    accepted_for_agent: bool
    voice_intent: str | None
    voice_action_name: str | None
    voice_latency_ms: int | None
    intent_ok: bool | None
    action_ok: bool | None
    slot_matches: dict[str, bool]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SttBenchmarkReport:
    generated_at: datetime
    stt_engine: str
    stt_model: str | None
    sample_count: int
    accepted_count: int
    blocked_count: int
    average_stt_processing_ms: float
    average_realtime_factor: float
    average_wer: float | None
    intent_accuracy: float | None
    action_accuracy: float | None
    slot_field_accuracy: float | None
    cases: tuple[SttBenchmarkCaseResult, ...]


def run_stt_benchmark(
    cases: tuple[SttBenchmarkCase, ...],
    adapter: SpeechToTextAdapter,
    *,
    service_factory: type[RestaurantMVPService] = RestaurantMVPService,
    generated_at: datetime | None = None,
) -> SttBenchmarkReport:
    if not cases:
        raise ValueError("at least one benchmark case is required.")
    results = tuple(_run_case(case, adapter, service_factory=service_factory) for case in cases)
    accepted = [result for result in results if result.accepted_for_agent]
    wers = [result.wer for result in results if result.wer is not None]
    intent_checks = [result.intent_ok for result in results if result.intent_ok is not None]
    action_checks = [result.action_ok for result in results if result.action_ok is not None]
    slot_values = [slot_ok for result in results for slot_ok in result.slot_matches.values()]
    return SttBenchmarkReport(
        generated_at=generated_at or datetime.now(UTC),
        stt_engine=adapter.config.engine,
        stt_model=adapter.config.model_path,
        sample_count=len(results),
        accepted_count=len(accepted),
        blocked_count=len(results) - len(accepted),
        average_stt_processing_ms=round(
            sum(result.stt_processing_ms for result in results) / len(results),
            2,
        ),
        average_realtime_factor=round(
            sum(result.realtime_factor for result in results) / len(results),
            4,
        ),
        average_wer=round(sum(wers) / len(wers), 4) if wers else None,
        intent_accuracy=_ratio(intent_checks),
        action_accuracy=_ratio(action_checks),
        slot_field_accuracy=_ratio(slot_values),
        cases=results,
    )


def _run_case(
    case: SttBenchmarkCase,
    adapter: SpeechToTextAdapter,
    *,
    service_factory: type[RestaurantMVPService],
) -> SttBenchmarkCaseResult:
    read_result = read_pcm16_wav(case.wav_path)
    vad = simple_energy_vad(read_result.audio, read_result.samples)
    stt_result = _transcribe_safely(adapter, case.wav_path)
    transcript_quality = evaluate_transcript_quality(
        stt_result.transcript,
        confidence=(
            case.confidence_override
            if case.confidence_override is not None
            else stt_result.confidence
        ),
    )
    accepted_for_agent = vad.has_speech and transcript_quality.accepted
    voice_intent = None
    voice_action_name = None
    voice_latency_ms = None
    intent_ok = None
    action_ok = None
    slot_matches: dict[str, bool] = {}
    if accepted_for_agent:
        started = perf_counter()
        agent = VoiceReservationAgent(service_factory())
        call = agent.start_call(started_at=datetime.now(UTC), source_channel="stt_benchmark")
        turn = agent.handle_turn(
            call.call_id,
            transcript=stt_result.transcript,
            confidence=stt_result.confidence or 0.95,
            observed_at=datetime.now(UTC),
        )
        voice_latency_ms = int(round((perf_counter() - started) * 1000))
        voice_intent = str(turn.intent)
        voice_action_name = turn.action_name
        intent_ok = None if case.expected_intent is None else voice_intent == case.expected_intent
        action_ok = (
            None
            if case.expected_action_name is None
            else voice_action_name == case.expected_action_name
        )
        if case.expected_slots:
            actual_slots = {
                "party_size": turn.call.reservation_draft.party_size,
                "requested_time_text": turn.call.reservation_draft.requested_time_text,
                "customer_name": turn.call.reservation_draft.customer_name,
                "phone": turn.call.reservation_draft.phone,
            }
            slot_matches = {
                field: actual_slots.get(field) == expected
                for field, expected in case.expected_slots.items()
            }

    return SttBenchmarkCaseResult(
        case_id=case.case_id,
        wav_path=case.wav_path,
        audio_duration_ms=read_result.audio.duration_ms,
        stt_engine=stt_result.engine,
        stt_model=stt_result.model,
        stt_processing_ms=stt_result.processing_ms,
        realtime_factor=(
            round(
                stt_result.processing_ms / read_result.audio.duration_ms,
                4,
            )
            if read_result.audio.duration_ms
            else 0.0
        ),
        transcript=stt_result.transcript,
        wer=(
            word_error_rate(case.expected_transcript, stt_result.transcript)
            if case.expected_transcript is not None
            else None
        ),
        vad=vad,
        transcript_quality=transcript_quality,
        accepted_for_agent=accepted_for_agent,
        voice_intent=voice_intent,
        voice_action_name=voice_action_name,
        voice_latency_ms=voice_latency_ms,
        intent_ok=intent_ok,
        action_ok=action_ok,
        slot_matches=slot_matches,
        error=stt_result.metadata.get("error") if stt_result.metadata else None,
    )


def _transcribe_safely(adapter: SpeechToTextAdapter, wav_path: str) -> TranscriptionResult:
    try:
        return adapter.transcribe(wav_path)
    except Exception as exc:  # noqa: BLE001 - benchmark must report backend failures.
        return TranscriptionResult(
            transcript="",
            engine=adapter.config.engine,
            model=adapter.config.model_path,
            language=adapter.config.language,
            processing_ms=0,
            confidence=0.0,
            metadata={"error": str(exc)},
        )


def _ratio(values: list[bool | None]) -> float | None:
    materialized = [bool(value) for value in values if value is not None]
    if not materialized:
        return None
    return round(sum(materialized) / len(materialized), 4)
