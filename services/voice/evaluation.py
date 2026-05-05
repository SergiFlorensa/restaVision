from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from services.evaluation.metrics import ClassificationReport, classification_report
from services.events.service import RestaurantMVPService
from services.voice.agent import VoiceReservationAgent
from services.voice.models import ReservationDraft, VoiceIntent

_REFERENCE_TS = datetime(2026, 5, 2, 19, 0, tzinfo=ZoneInfo("Europe/Madrid"))


@dataclass(frozen=True, slots=True)
class VoiceEvaluationCase:
    case_id: str
    transcript: str
    expected_intent: VoiceIntent
    expected_action_name: str
    expected_call_status: str | None = None
    expected_scenario_id: str | None = None
    expected_missing_fields: tuple[str, ...] = ()
    expected_slots: dict[str, object] = field(default_factory=dict)
    expected_escalated: bool | None = None
    confidence: float = 0.95
    observed_at: datetime = _REFERENCE_TS
    caller_phone: str | None = None


@dataclass(frozen=True, slots=True)
class VoiceCaseEvaluationResult:
    case_id: str
    transcript: str
    expected_intent: str
    actual_intent: str
    intent_ok: bool
    expected_action_name: str
    actual_action_name: str
    action_ok: bool
    expected_call_status: str | None
    actual_call_status: str
    call_status_ok: bool
    expected_scenario_id: str | None
    actual_scenario_id: str | None
    scenario_ok: bool
    expected_missing_fields: tuple[str, ...]
    actual_missing_fields: tuple[str, ...]
    missing_fields_ok: bool
    expected_slots: dict[str, object]
    actual_slots: dict[str, object]
    slot_matches: dict[str, bool]
    slots_ok: bool
    expected_escalated: bool | None
    actual_escalated: bool
    escalated_ok: bool
    reply_text: str


@dataclass(frozen=True, slots=True)
class VoiceEvaluationClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True, slots=True)
class VoiceEvaluationReport:
    source: str
    generated_at: datetime
    sample_count: int
    intent_accuracy: float
    intent_macro_precision: float
    intent_macro_recall: float
    intent_macro_f1: float
    action_accuracy: float
    call_status_accuracy: float
    scenario_accuracy: float
    missing_fields_accuracy: float
    slot_exact_match_rate: float
    slot_field_accuracy: float
    escalation_accuracy: float
    failed_case_ids: tuple[str, ...]
    per_intent: dict[str, VoiceEvaluationClassMetrics]
    confusion_matrix: dict[str, dict[str, int]]
    cases: tuple[VoiceCaseEvaluationResult, ...]


BASELINE_VOICE_EVALUATION_CASES: tuple[VoiceEvaluationCase, ...] = (
    VoiceEvaluationCase(
        case_id="create_full_reservation",
        transcript=(
            "Queria reservar mesa para 4 a las 21:30 a nombre de Sergio, mi telefono es 600123123"
        ),
        expected_intent=VoiceIntent.CREATE_RESERVATION,
        expected_action_name="utter_confirm_customer_name",
        expected_call_status="collecting_details",
        expected_missing_fields=("customer_name_confirmation",),
        expected_slots={
            "party_size": 4,
            "requested_time_text": "02/05/2026 21:30",
            "customer_name": "Sergio",
            "phone": "600123123",
        },
        expected_escalated=False,
    ),
    VoiceEvaluationCase(
        case_id="create_relative_time_words",
        transcript=("Reserva para cuatro manana a las nueve a nombre de Lucia telefono 611222333"),
        expected_intent=VoiceIntent.CREATE_RESERVATION,
        expected_action_name="utter_confirm_customer_name",
        expected_call_status="collecting_details",
        expected_missing_fields=("customer_name_confirmation",),
        expected_slots={
            "party_size": 4,
            "requested_time_text": "03/05/2026 21:00",
            "customer_name": "Lucia",
            "phone": "611222333",
        },
        expected_escalated=False,
    ),
    VoiceEvaluationCase(
        case_id="partial_date_requires_time",
        transcript="Queria reservar mesa para 3 el viernes a nombre de Carla telefono 644555666",
        expected_intent=VoiceIntent.CREATE_RESERVATION,
        expected_action_name="utter_ask_requested_time",
        expected_call_status="collecting_details",
        expected_missing_fields=("requested_time_text",),
        expected_slots={
            "party_size": 3,
            "requested_date_text": "08/05/2026",
            "customer_name": "Carla",
            "phone": "644555666",
        },
        expected_escalated=False,
    ),
    VoiceEvaluationCase(
        case_id="availability_offer",
        transcript="Teneis mesa para 2 a las 20:00?",
        expected_intent=VoiceIntent.CHECK_AVAILABILITY,
        expected_action_name="utter_offer_reservation",
        expected_call_status="open",
        expected_slots={
            "party_size": 2,
            "requested_time_text": "02/05/2026 20:00",
        },
        expected_escalated=False,
    ),
    VoiceEvaluationCase(
        case_id="cancel_needs_identifier",
        transcript="Quiero cancelar mi reserva",
        expected_intent=VoiceIntent.CANCEL_RESERVATION,
        expected_action_name="utter_ask_reservation_identifier",
        expected_call_status="open",
        expected_missing_fields=("phone_or_customer_name",),
        expected_escalated=False,
    ),
    VoiceEvaluationCase(
        case_id="allergen_interrupts",
        transcript=(
            "Queria reservar mesa para 2 manana a las 21:00 a nombre de Ana "
            "telefono 655111222, soy celiaco"
        ),
        expected_intent=VoiceIntent.SPECIAL_REQUEST,
        expected_action_name="action_escalate_to_manager",
        expected_call_status="escalated",
        expected_scenario_id="allergens",
        expected_escalated=True,
    ),
    VoiceEvaluationCase(
        case_id="opening_hours_escalates_without_kb",
        transcript="Hola, queria saber el horario de cocina",
        expected_intent=VoiceIntent.INFORMATION_REQUEST,
        expected_action_name="action_escalate_to_manager",
        expected_call_status="escalated",
        expected_scenario_id="opening_hours",
        expected_escalated=True,
    ),
    VoiceEvaluationCase(
        case_id="complaint_escalates",
        transcript="Quiero poner una reclamacion por una mala experiencia",
        expected_intent=VoiceIntent.COMPLAINT,
        expected_action_name="action_escalate_to_manager",
        expected_call_status="escalated",
        expected_scenario_id="complaint",
        expected_escalated=True,
    ),
    VoiceEvaluationCase(
        case_id="low_stt_confidence_escalates",
        transcript="ruido de llamada no se entiende",
        expected_intent=VoiceIntent.UNKNOWN,
        expected_action_name="action_escalate_to_manager",
        expected_call_status="escalated",
        expected_escalated=True,
        confidence=0.3,
    ),
    VoiceEvaluationCase(
        case_id="manager_request_escalates",
        transcript="Pasame con el encargado por favor",
        expected_intent=VoiceIntent.SPEAK_TO_MANAGER,
        expected_action_name="action_escalate_to_manager",
        expected_call_status="escalated",
        expected_escalated=True,
    ),
)


def evaluate_voice_agent_baseline(
    *,
    cases: tuple[VoiceEvaluationCase, ...] = BASELINE_VOICE_EVALUATION_CASES,
    service_factory: Callable[[], RestaurantMVPService] = RestaurantMVPService,
    generated_at: datetime | None = None,
) -> VoiceEvaluationReport:
    if not cases:
        raise ValueError("at least one voice evaluation case is required.")

    results = tuple(_evaluate_case(case, service_factory=service_factory) for case in cases)
    intent_report = classification_report(
        [result.expected_intent for result in results],
        [result.actual_intent for result in results],
    )
    slot_field_total = sum(len(result.slot_matches) for result in results)
    slot_field_ok = sum(
        1 for result in results for field_ok in result.slot_matches.values() if field_ok
    )
    failed_case_ids = tuple(
        result.case_id
        for result in results
        if not (
            result.intent_ok
            and result.action_ok
            and result.call_status_ok
            and result.scenario_ok
            and result.missing_fields_ok
            and result.slots_ok
            and result.escalated_ok
        )
    )

    return VoiceEvaluationReport(
        source="ed3book.pdf: classification, NER, temporal normalization, ASR evaluation",
        generated_at=generated_at or datetime.now(ZoneInfo("Europe/Madrid")),
        sample_count=len(results),
        intent_accuracy=round(intent_report.accuracy, 4),
        intent_macro_precision=round(intent_report.macro_precision, 4),
        intent_macro_recall=round(intent_report.macro_recall, 4),
        intent_macro_f1=round(intent_report.macro_f1, 4),
        action_accuracy=_ratio(result.action_ok for result in results),
        call_status_accuracy=_ratio(result.call_status_ok for result in results),
        scenario_accuracy=_ratio(result.scenario_ok for result in results),
        missing_fields_accuracy=_ratio(result.missing_fields_ok for result in results),
        slot_exact_match_rate=_ratio(result.slots_ok for result in results),
        slot_field_accuracy=round(slot_field_ok / slot_field_total, 4) if slot_field_total else 1.0,
        escalation_accuracy=_ratio(result.escalated_ok for result in results),
        failed_case_ids=failed_case_ids,
        per_intent=_serialize_class_metrics(intent_report),
        confusion_matrix=_serialize_confusion_matrix(intent_report),
        cases=results,
    )


def _evaluate_case(
    case: VoiceEvaluationCase,
    *,
    service_factory: Callable[[], RestaurantMVPService],
) -> VoiceCaseEvaluationResult:
    agent = VoiceReservationAgent(service_factory())
    call = agent.start_call(
        caller_phone=case.caller_phone,
        source_channel="evaluation_corpus",
        started_at=case.observed_at,
    )
    result = agent.handle_turn(
        call.call_id,
        transcript=case.transcript,
        confidence=case.confidence,
        observed_at=case.observed_at,
    )
    actual_slots = _draft_slots(result.call.reservation_draft)
    slot_matches = {
        field_name: actual_slots.get(field_name) == expected_value
        for field_name, expected_value in case.expected_slots.items()
    }
    actual_status = str(result.call.status)
    expected_intent = str(case.expected_intent)
    actual_intent = str(result.intent)
    expected_escalated = case.expected_escalated
    return VoiceCaseEvaluationResult(
        case_id=case.case_id,
        transcript=case.transcript,
        expected_intent=expected_intent,
        actual_intent=actual_intent,
        intent_ok=expected_intent == actual_intent,
        expected_action_name=case.expected_action_name,
        actual_action_name=result.action_name,
        action_ok=case.expected_action_name == result.action_name,
        expected_call_status=case.expected_call_status,
        actual_call_status=actual_status,
        call_status_ok=case.expected_call_status is None
        or case.expected_call_status == actual_status,
        expected_scenario_id=case.expected_scenario_id,
        actual_scenario_id=result.call.scenario_id,
        scenario_ok=case.expected_scenario_id == result.call.scenario_id,
        expected_missing_fields=case.expected_missing_fields,
        actual_missing_fields=tuple(result.missing_fields),
        missing_fields_ok=case.expected_missing_fields == tuple(result.missing_fields),
        expected_slots=case.expected_slots,
        actual_slots=actual_slots,
        slot_matches=slot_matches,
        slots_ok=all(slot_matches.values()),
        expected_escalated=expected_escalated,
        actual_escalated=result.escalated,
        escalated_ok=expected_escalated is None or expected_escalated == result.escalated,
        reply_text=result.reply_text,
    )


def _draft_slots(draft: ReservationDraft) -> dict[str, object]:
    return {
        "party_size": draft.party_size,
        "requested_date_text": draft.requested_date_text,
        "date_parser": draft.date_parser,
        "requested_time_text": draft.requested_time_text,
        "time_parser": draft.time_parser,
        "customer_name": draft.customer_name,
        "phone": draft.phone,
        "preferred_zone_id": draft.preferred_zone_id,
    }


def _serialize_class_metrics(
    report: ClassificationReport,
) -> dict[str, VoiceEvaluationClassMetrics]:
    return {
        label: VoiceEvaluationClassMetrics(
            precision=round(metrics.precision, 4),
            recall=round(metrics.recall, 4),
            f1=round(metrics.f1, 4),
            support=metrics.support,
        )
        for label, metrics in report.per_class.items()
    }


def _serialize_confusion_matrix(report: ClassificationReport) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for row_index, expected_label in enumerate(report.confusion.labels):
        matrix[expected_label] = {}
        for column_index, predicted_label in enumerate(report.confusion.labels):
            matrix[expected_label][predicted_label] = int(
                report.confusion.matrix[row_index, column_index]
            )
    return matrix


def _ratio(values: object) -> float:
    materialized = tuple(bool(value) for value in values)
    if not materialized:
        return 0.0
    return round(sum(materialized) / len(materialized), 4)
