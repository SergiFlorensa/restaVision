from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class VoiceIntent(StrEnum):
    CREATE_RESERVATION = "create_reservation"
    CANCEL_RESERVATION = "cancel_reservation"
    MODIFY_RESERVATION = "modify_reservation"
    CHECK_AVAILABILITY = "check_availability"
    CONFIRM_ARRIVAL = "confirm_arrival"
    INFORMATION_REQUEST = "information_request"
    SPECIAL_REQUEST = "special_request"
    COMPLAINT = "complaint"
    OPERATIONAL_NOTICE = "operational_notice"
    THIRD_PARTY = "third_party"
    SPEAK_TO_MANAGER = "speak_to_manager"
    UNKNOWN = "unknown"


class VoiceCallStatus(StrEnum):
    OPEN = "open"
    COLLECTING_DETAILS = "collecting_details"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CLOSED = "closed"


class VoiceReservationStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ReservationDraft:
    party_size: int | None = None
    requested_date: date | None = None
    requested_date_text: str | None = None
    date_parser: str | None = None
    requested_time_text: str | None = None
    requested_at: datetime | None = None
    time_parser: str | None = None
    customer_name: str | None = None
    customer_name_confirmed: bool = False
    customer_name_confirmation_attempts: int = 0
    customer_name_spelling_requested: bool = False
    phone: str | None = None
    preferred_zone_id: str | None = None


@dataclass(slots=True)
class VoiceTurn:
    turn_id: str
    ts: datetime
    speaker: str
    transcript: str
    intent: VoiceIntent
    confidence: float


@dataclass(slots=True)
class VoiceReservation:
    reservation_id: str
    customer_name: str
    phone: str
    party_size: int
    requested_time_text: str
    requested_at: datetime | None
    table_id: str | None
    status: VoiceReservationStatus
    created_at: datetime
    source_call_id: str
    notes: str | None = None


@dataclass(slots=True)
class VoiceCall:
    call_id: str
    started_at: datetime
    source_channel: str
    caller_phone: str | None = None
    status: VoiceCallStatus = VoiceCallStatus.OPEN
    intent: VoiceIntent = VoiceIntent.UNKNOWN
    reservation_draft: ReservationDraft = field(default_factory=ReservationDraft)
    reservation_id: str | None = None
    scenario_id: str | None = None
    turns: list[VoiceTurn] = field(default_factory=list)
    escalated_reason: str | None = None
    ended_at: datetime | None = None
    background_reply_status: str = "idle"
    background_reply_text: str | None = None
    background_reply_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    available: bool
    table_id: str | None
    reason: str
    confidence: float
    pressure_mode: str = "normal"
    pressure_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VoiceTurnResult:
    call: VoiceCall
    reply_text: str
    intent: VoiceIntent
    confidence: float
    action_name: str = "utter_reply"
    action_payload: dict[str, object] = field(default_factory=dict)
    missing_fields: tuple[str, ...] = ()
    reservation: VoiceReservation | None = None
    availability: AvailabilityResult | None = None
    escalated: bool = False


@dataclass(frozen=True, slots=True)
class VoiceGatekeeperStatus:
    mode: str
    score: int
    ready_tables: int
    total_tables: int
    waiting_queue_groups: int
    active_reservations: int
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VoiceMetrics:
    total_calls: int
    open_calls: int
    confirmed_calls: int
    rejected_calls: int
    escalated_calls: int
    closed_calls: int
    total_reservations: int
    confirmed_reservations: int
    cancelled_reservations: int
    auto_resolution_rate: float
    escalation_rate: float
    average_turns_per_call: float
    gatekeeper: VoiceGatekeeperStatus
