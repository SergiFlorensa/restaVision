from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from services.events.service import RestaurantMVPService
from services.voice.models import (
    AvailabilityResult,
    ReservationDraft,
    VoiceCall,
    VoiceCallStatus,
    VoiceGatekeeperStatus,
    VoiceIntent,
    VoiceMetrics,
    VoiceReservation,
    VoiceReservationStatus,
    VoiceTurn,
    VoiceTurnResult,
)
from services.voice.scenarios import VoiceScenario, classify_voice_scenario
from services.voice.speech_text import reservation_time_for_speech
from services.voice.time_parser import parse_reservation_date, parse_reservation_time

_SPANISH_NUMBERS = {
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
}

_SPANISH_DIGIT_WORDS = {
    "cero": "0",
    "ceros": "0",
    "un": "1",
    "uno": "1",
    "unos": "1",
    "una": "1",
    "unas": "1",
    "dos": "2",
    "tres": "3",
    "cuatro": "4",
    "cinco": "5",
    "seis": "6",
    "siete": "7",
    "ocho": "8",
    "nueve": "9",
}

_SPANISH_TEENS = {
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintiun": 21,
    "veintiuna": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
}

_SPANISH_TENS = {
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
}

_SPANISH_HUNDREDS = {
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "cuatrocientos": 400,
    "cuatrocientas": 400,
    "quinientos": 500,
    "quinientas": 500,
    "seiscientos": 600,
    "seiscientas": 600,
    "setecientos": 700,
    "setecientas": 700,
    "ochocientos": 800,
    "ochocientas": 800,
    "novecientos": 900,
    "novecientas": 900,
}

_CUSTOMER_NAME_ALIASES = {
    "seres": "Sergi",
    "seres y": "Sergi",
    "sergi": "Sergi",
    "sergy": "Sergi",
    "serji": "Sergi",
    "sergio": "Sergio",
}

_NAME_STOP_WORDS = {
    "mi",
    "telefono",
    "numero",
    "para",
    "a",
    "las",
    "es",
    "seria",
    "gracias",
    "y",
    "correcto",
    "no",
    "nombre",
}

_SPELLING_LETTERS = {
    "a": "a",
    "be": "b",
    "b": "b",
    "ce": "c",
    "c": "c",
    "de": "d",
    "d": "d",
    "e": "e",
    "efe": "f",
    "f": "f",
    "ge": "g",
    "g": "g",
    "hache": "h",
    "i": "i",
    "jota": "j",
    "ka": "k",
    "k": "k",
    "ele": "l",
    "l": "l",
    "eme": "m",
    "m": "m",
    "ene": "n",
    "n": "n",
    "enie": "ñ",
    "o": "o",
    "pe": "p",
    "p": "p",
    "cu": "q",
    "q": "q",
    "erre": "r",
    "r": "r",
    "ese": "s",
    "s": "s",
    "te": "t",
    "t": "t",
    "u": "u",
    "uve": "v",
    "ve": "v",
    "v": "v",
    "doble u": "w",
    "uve doble": "w",
    "w": "w",
    "equis": "x",
    "x": "x",
    "ye": "y",
    "i griega": "y",
    "y": "y",
    "zeta": "z",
    "z": "z",
}


class VoiceReservationAgent:
    """Stateful prototype for voice reservation calls.

    Asterisk, a browser microphone, or a future STT service can all feed this
    agent with transcripts. The agent keeps the business decision deterministic.
    """

    def __init__(
        self,
        restaurant_service: RestaurantMVPService,
        *,
        max_auto_party_size: int = 6,
        low_confidence_threshold: float = 0.55,
        guarded_ready_table_ratio: float = 0.25,
    ) -> None:
        self.restaurant_service = restaurant_service
        self.max_auto_party_size = max_auto_party_size
        self.low_confidence_threshold = low_confidence_threshold
        self.guarded_ready_table_ratio = guarded_ready_table_ratio
        self.calls: dict[str, VoiceCall] = {}
        self.reservations: dict[str, VoiceReservation] = {}

    def start_call(
        self,
        *,
        caller_phone: str | None = None,
        source_channel: str = "browser_simulator",
        started_at: datetime | None = None,
    ) -> VoiceCall:
        call = VoiceCall(
            call_id=self._new_id("voice_call"),
            started_at=started_at or datetime.now(UTC),
            caller_phone=caller_phone,
            source_channel=source_channel,
        )
        if caller_phone:
            call.reservation_draft.phone = _normalize_phone(caller_phone)
        self.calls[call.call_id] = call
        return call

    def get_call(self, call_id: str) -> VoiceCall:
        try:
            return self.calls[call_id]
        except KeyError as exc:
            raise KeyError(f"Unknown call_id: {call_id}") from exc

    def list_calls(self) -> list[VoiceCall]:
        return sorted(self.calls.values(), key=lambda item: item.started_at, reverse=True)

    def list_reservations(self) -> list[VoiceReservation]:
        return sorted(
            self.reservations.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )

    def gatekeeper_status(self) -> VoiceGatekeeperStatus:
        tables = self.restaurant_service.list_table_snapshots()
        queue_groups = [
            group
            for group in self.restaurant_service.list_queue_groups()
            if str(group.status) == "waiting"
        ]
        ready_tables = sum(1 for table in tables if table.state.value == "ready")
        occupied_tables = sum(1 for table in tables if table.state.value == "occupied")
        pending_cleaning_tables = sum(
            1 for table in tables if table.state.value == "pending_cleaning"
        )
        total_tables = len(tables)
        active_reservations = sum(
            1
            for reservation in self.reservations.values()
            if reservation.status is VoiceReservationStatus.CONFIRMED
        )
        ready_ratio = ready_tables / total_tables if total_tables else 0.0
        score = 0
        reasons: list[str] = []
        if total_tables and ready_tables == 0:
            score += 45
            reasons.append("no_ready_tables")
        elif total_tables and ready_ratio <= self.guarded_ready_table_ratio:
            score += 20
            reasons.append("low_ready_table_ratio")
        if queue_groups:
            score += min(35, 15 + len(queue_groups) * 8)
            reasons.append("physical_queue_waiting")
        if pending_cleaning_tables:
            score += min(20, pending_cleaning_tables * 8)
            reasons.append("tables_pending_cleaning")
        if total_tables and occupied_tables == total_tables:
            score += 20
            reasons.append("all_tables_occupied")
        if active_reservations >= max(2, total_tables):
            score += 10
            reasons.append("reservation_stack_active")

        if score >= 55:
            mode = "critical"
        elif score >= 25:
            mode = "guarded"
        else:
            mode = "normal"
        return VoiceGatekeeperStatus(
            mode=mode,
            score=min(score, 100),
            ready_tables=ready_tables,
            total_tables=total_tables,
            waiting_queue_groups=len(queue_groups),
            active_reservations=active_reservations,
            reasons=tuple(reasons),
        )

    def metrics(self) -> VoiceMetrics:
        total_calls = len(self.calls)
        open_calls = sum(
            1
            for call in self.calls.values()
            if call.status in {VoiceCallStatus.OPEN, VoiceCallStatus.COLLECTING_DETAILS}
        )
        confirmed_calls = sum(
            1 for call in self.calls.values() if call.status is VoiceCallStatus.CONFIRMED
        )
        rejected_calls = sum(
            1 for call in self.calls.values() if call.status is VoiceCallStatus.REJECTED
        )
        escalated_calls = sum(
            1 for call in self.calls.values() if call.status is VoiceCallStatus.ESCALATED
        )
        closed_calls = sum(
            1 for call in self.calls.values() if call.status is VoiceCallStatus.CLOSED
        )
        total_reservations = len(self.reservations)
        confirmed_reservations = sum(
            1
            for reservation in self.reservations.values()
            if reservation.status is VoiceReservationStatus.CONFIRMED
        )
        cancelled_reservations = sum(
            1
            for reservation in self.reservations.values()
            if reservation.status is VoiceReservationStatus.CANCELLED
        )
        handled_calls = confirmed_calls + rejected_calls + escalated_calls + closed_calls
        auto_resolved = confirmed_calls + rejected_calls + closed_calls
        total_turns = sum(len(call.turns) for call in self.calls.values())
        return VoiceMetrics(
            total_calls=total_calls,
            open_calls=open_calls,
            confirmed_calls=confirmed_calls,
            rejected_calls=rejected_calls,
            escalated_calls=escalated_calls,
            closed_calls=closed_calls,
            total_reservations=total_reservations,
            confirmed_reservations=confirmed_reservations,
            cancelled_reservations=cancelled_reservations,
            auto_resolution_rate=(
                round(auto_resolved / handled_calls, 3) if handled_calls else 0.0
            ),
            escalation_rate=round(escalated_calls / handled_calls, 3) if handled_calls else 0.0,
            average_turns_per_call=round(total_turns / total_calls, 2) if total_calls else 0.0,
            gatekeeper=self.gatekeeper_status(),
        )

    def handle_turn(
        self,
        call_id: str,
        *,
        transcript: str,
        confidence: float = 1.0,
        observed_at: datetime | None = None,
    ) -> VoiceTurnResult:
        call = self.get_call(call_id)
        timestamp = observed_at or datetime.now(UTC)
        normalized = _normalize_text(transcript)
        scenario = classify_voice_scenario(normalized)
        intent = self._detect_intent(normalized, call)
        if scenario is not None and (
            intent is VoiceIntent.UNKNOWN or scenario.interrupts_reservation
        ):
            intent = scenario.intent
        if call.intent is VoiceIntent.UNKNOWN and intent is not VoiceIntent.UNKNOWN:
            call.intent = intent
        elif intent is VoiceIntent.UNKNOWN:
            intent = call.intent
        turn = VoiceTurn(
            turn_id=self._new_id("voice_turn"),
            ts=timestamp,
            speaker="caller",
            transcript=transcript,
            intent=intent,
            confidence=confidence,
        )
        call.turns.append(turn)

        if confidence < self.low_confidence_threshold:
            return self._escalate(
                call,
                reason="low_stt_confidence",
                reply_text=(
                    "No he entendido la llamada con suficiente claridad. Le paso con el encargado."
                ),
            )

        if scenario is not None and (scenario.interrupts_reservation or intent is scenario.intent):
            return self._handle_scenario(call, scenario)
        if intent is VoiceIntent.CREATE_RESERVATION:
            return self._handle_create_reservation(call, normalized, confidence, timestamp)
        if intent is VoiceIntent.CHECK_AVAILABILITY:
            return self._handle_check_availability(call, normalized, confidence, timestamp)
        if intent is VoiceIntent.CANCEL_RESERVATION:
            return self._handle_cancel_reservation(call, normalized, confidence, timestamp)
        if intent is VoiceIntent.MODIFY_RESERVATION:
            return self._escalate(
                call,
                reason="modify_reservation_requires_manager",
                reply_text=(
                    "Para modificar una reserva prefiero pasarle con el encargado y evitar errores."
                ),
            )
        if intent in {VoiceIntent.CONFIRM_ARRIVAL, VoiceIntent.SPEAK_TO_MANAGER}:
            return self._escalate(
                call,
                reason=intent.value,
                reply_text="Un momento, le paso con el encargado.",
            )
        return VoiceTurnResult(
            call=call,
            reply_text=(
                "Puedo ayudarle con una reserva, una cancelacion o una consulta "
                "de disponibilidad. Que necesita?"
            ),
            intent=VoiceIntent.UNKNOWN,
            confidence=confidence,
            action_name="utter_ask_intent",
            action_payload={"missing_field": "intent"},
            missing_fields=("intent",),
        )

    def _handle_create_reservation(
        self,
        call: VoiceCall,
        normalized: str,
        confidence: float,
        timestamp: datetime,
    ) -> VoiceTurnResult:
        call.status = VoiceCallStatus.COLLECTING_DETAILS
        name_confirmation = _detect_name_confirmation(normalized)
        if (
            call.reservation_draft.customer_name is not None
            and not call.reservation_draft.customer_name_confirmed
        ):
            if name_confirmation is False:
                call.reservation_draft.customer_name_confirmation_attempts += 1
                corrected_name = _extract_spelled_customer_name(
                    normalized
                ) or _extract_customer_name_correction(normalized)
                call.reservation_draft.customer_name = corrected_name
                call.reservation_draft.customer_name_confirmed = False
                call.reservation_draft.customer_name_spelling_requested = (
                    call.reservation_draft.customer_name_confirmation_attempts >= 1
                )
                if corrected_name is not None:
                    return self._ask_customer_name_confirmation(call, confidence)
                return VoiceTurnResult(
                    call=call,
                    reply_text=(
                        "Disculpe, para anotarlo bien, puede deletrearme el nombre letra a letra?"
                    ),
                    intent=VoiceIntent.CREATE_RESERVATION,
                    confidence=confidence,
                    action_name="utter_ask_customer_name",
                    action_payload={"missing_field": "customer_name"},
                    missing_fields=("customer_name",),
                )
            if name_confirmation is True:
                call.reservation_draft.customer_name_confirmed = True
                call.reservation_draft.customer_name_spelling_requested = False

        self._merge_entities(
            call.reservation_draft,
            normalized,
            reference=timestamp,
            phone_expected=_is_phone_expected_for_reservation(call.reservation_draft),
            name_expected=_is_customer_name_expected(call.reservation_draft),
        )
        if (
            call.reservation_draft.customer_name is not None
            and not call.reservation_draft.customer_name_confirmed
        ):
            return self._ask_customer_name_confirmation(call, confidence)

        missing = self._missing_reservation_fields(call.reservation_draft)
        if missing:
            return VoiceTurnResult(
                call=call,
                reply_text=self._question_for_missing_field(missing[0]),
                intent=VoiceIntent.CREATE_RESERVATION,
                confidence=confidence,
                action_name=self._action_for_missing_field(missing[0]),
                action_payload={"missing_field": missing[0]},
                missing_fields=missing,
            )

        availability = self._check_availability(call.reservation_draft)
        if not availability.available and availability.reason == "service_pressure_overflow":
            return self._escalate(
                call,
                reason=availability.reason,
                reply_text=(
                    "Ahora mismo la sala esta en un punto de mucha carga. "
                    "Para no darle una reserva que no podamos cumplir, le paso con el encargado."
                ),
                availability=availability,
            )
        if not availability.available:
            call.status = VoiceCallStatus.REJECTED
            return VoiceTurnResult(
                call=call,
                reply_text=(
                    "Ahora mismo no puedo garantizar esa mesa. "
                    "Puedo dejar aviso al encargado o buscar otra hora."
                ),
                intent=VoiceIntent.CREATE_RESERVATION,
                confidence=confidence,
                action_name="action_reject_reservation",
                action_payload={
                    "reason": availability.reason,
                    "pressure_mode": availability.pressure_mode,
                },
                availability=availability,
            )

        reservation = self._confirm_reservation(call, availability, timestamp)
        call.status = VoiceCallStatus.CONFIRMED
        call.reservation_id = reservation.reservation_id
        spoken_time = reservation_time_for_speech(
            reservation.requested_at,
            reservation.requested_time_text,
        )
        return VoiceTurnResult(
            call=call,
            reply_text=(
                f"Reserva confirmada para {reservation.party_size} personas "
                f"{spoken_time}, "
                f"a nombre de {reservation.customer_name}. "
                "Muchas gracias, le esperamos en la Piemontesa de Passeig de Prim."
            ),
            intent=VoiceIntent.CREATE_RESERVATION,
            confidence=confidence,
            action_name="action_confirm_reservation",
            action_payload={
                "reservation_id": reservation.reservation_id,
                "table_id": reservation.table_id,
            },
            reservation=reservation,
            availability=availability,
        )

    def _ask_customer_name_confirmation(
        self,
        call: VoiceCall,
        confidence: float,
    ) -> VoiceTurnResult:
        customer_name = call.reservation_draft.customer_name
        return VoiceTurnResult(
            call=call,
            reply_text=f"He entendido {customer_name}. Es correcto el nombre?",
            intent=VoiceIntent.CREATE_RESERVATION,
            confidence=confidence,
            action_name="utter_confirm_customer_name",
            action_payload={"customer_name": customer_name},
            missing_fields=("customer_name_confirmation",),
        )

    def _handle_check_availability(
        self,
        call: VoiceCall,
        normalized: str,
        confidence: float,
        timestamp: datetime,
    ) -> VoiceTurnResult:
        self._merge_entities(
            call.reservation_draft,
            normalized,
            reference=timestamp,
            phone_expected=False,
        )
        missing = tuple(
            field
            for field in ("party_size", "requested_time_text")
            if getattr(call.reservation_draft, field) is None
        )
        if missing:
            return VoiceTurnResult(
                call=call,
                reply_text=self._question_for_missing_field(missing[0]),
                intent=VoiceIntent.CHECK_AVAILABILITY,
                confidence=confidence,
                action_name=self._action_for_missing_field(missing[0]),
                action_payload={"missing_field": missing[0]},
                missing_fields=missing,
            )

        availability = self._check_availability(call.reservation_draft)
        if availability.available:
            spoken_time = reservation_time_for_speech(
                call.reservation_draft.requested_at,
                str(call.reservation_draft.requested_time_text),
            )
            reply = (
                f"Si, puedo ofrecer mesa para {call.reservation_draft.party_size} "
                f"personas {spoken_time}. "
                "Quiere que la reserve?"
            )
            action_name = "utter_offer_reservation"
        else:
            reply = (
                "Ahora mismo no puedo garantizar disponibilidad para esa peticion. "
                "Puedo pasar aviso al encargado."
            )
            action_name = "utter_reject_availability"
        return VoiceTurnResult(
            call=call,
            reply_text=reply,
            intent=VoiceIntent.CHECK_AVAILABILITY,
            confidence=confidence,
            action_name=action_name,
            action_payload={
                "available": availability.available,
                "reason": availability.reason,
                "table_id": availability.table_id,
            },
            availability=availability,
        )

    def _handle_cancel_reservation(
        self,
        call: VoiceCall,
        normalized: str,
        confidence: float,
        timestamp: datetime,
    ) -> VoiceTurnResult:
        self._merge_entities(
            call.reservation_draft,
            normalized,
            reference=timestamp,
            phone_expected=True,
        )
        reservation = self._find_reservation(call.reservation_draft)
        if reservation is None:
            missing = self._missing_cancel_fields(call.reservation_draft)
            if missing:
                return VoiceTurnResult(
                    call=call,
                    reply_text=self._question_for_missing_field(missing[0]),
                    intent=VoiceIntent.CANCEL_RESERVATION,
                    confidence=confidence,
                    action_name=self._action_for_missing_field(missing[0]),
                    action_payload={"missing_field": missing[0]},
                    missing_fields=missing,
                )
            return self._escalate(
                call,
                reason="reservation_not_found",
                reply_text=(
                    "No localizo la reserva con esos datos. "
                    "Le paso con el encargado para revisarlo."
                ),
            )

        cancelled = replace(reservation, status=VoiceReservationStatus.CANCELLED)
        self.reservations[cancelled.reservation_id] = cancelled
        call.status = VoiceCallStatus.CLOSED
        call.reservation_id = cancelled.reservation_id
        call.ended_at = timestamp
        self.restaurant_service.record_operational_action(
            action_type="reservation_cancelled",
            table_id=cancelled.table_id,
            target_channel="voice_agent",
            message=(
                f"Reserva cancelada: {cancelled.customer_name}, "
                f"{cancelled.party_size} personas, {cancelled.requested_time_text}"
            ),
            payload={
                "reservation_id": cancelled.reservation_id,
                "source_call_id": call.call_id,
            },
            ts=timestamp,
        )
        return VoiceTurnResult(
            call=call,
            reply_text=(
                f"Reserva a nombre de {cancelled.customer_name} cancelada. Gracias por avisar."
            ),
            intent=VoiceIntent.CANCEL_RESERVATION,
            confidence=confidence,
            action_name="action_cancel_reservation",
            action_payload={"reservation_id": cancelled.reservation_id},
            reservation=cancelled,
        )

    def _confirm_reservation(
        self,
        call: VoiceCall,
        availability: AvailabilityResult,
        timestamp: datetime,
    ) -> VoiceReservation:
        draft = call.reservation_draft
        reservation = VoiceReservation(
            reservation_id=self._new_id("reservation"),
            customer_name=str(draft.customer_name),
            phone=str(draft.phone),
            party_size=int(draft.party_size or 0),
            requested_time_text=str(draft.requested_time_text),
            requested_at=draft.requested_at,
            table_id=availability.table_id,
            status=VoiceReservationStatus.CONFIRMED,
            created_at=timestamp,
            source_call_id=call.call_id,
        )
        self.reservations[reservation.reservation_id] = reservation
        self.restaurant_service.record_operational_action(
            action_type="reservation_confirmed",
            table_id=reservation.table_id,
            target_channel="voice_agent",
            message=(
                f"Reserva confirmada: {reservation.customer_name}, "
                f"{reservation.party_size} personas, {reservation.requested_time_text}"
            ),
            payload={
                "reservation_id": reservation.reservation_id,
                "source_call_id": call.call_id,
                "phone": reservation.phone,
                "requested_at": (
                    reservation.requested_at.isoformat()
                    if reservation.requested_at is not None
                    else None
                ),
                "time_parser": draft.time_parser,
            },
            ts=timestamp,
        )
        return reservation

    def _check_availability(self, draft: ReservationDraft) -> AvailabilityResult:
        gatekeeper = self.gatekeeper_status()
        if draft.party_size is None:
            return AvailabilityResult(
                False,
                None,
                "party_size_missing",
                0.0,
                gatekeeper.mode,
                gatekeeper.reasons,
            )
        if draft.party_size > self.max_auto_party_size:
            return AvailabilityResult(
                False,
                None,
                "party_size_requires_manager",
                0.45,
                gatekeeper.mode,
                gatekeeper.reasons,
            )
        if gatekeeper.mode in {"guarded", "critical"} and gatekeeper.waiting_queue_groups > 0:
            return AvailabilityResult(
                False,
                None,
                "service_pressure_overflow",
                0.42,
                gatekeeper.mode,
                gatekeeper.reasons,
            )

        compatible_tables = [
            table
            for table in self.restaurant_service.list_table_snapshots()
            if table.capacity >= draft.party_size and table.state.value == "ready"
        ]
        if not compatible_tables:
            return AvailabilityResult(
                False,
                None,
                "no_ready_table_for_party_size",
                0.5,
                gatekeeper.mode,
                gatekeeper.reasons,
            )

        best_table = sorted(compatible_tables, key=lambda table: table.capacity)[0]
        return AvailabilityResult(
            available=True,
            table_id=best_table.table_id,
            reason="ready_table_with_capacity",
            confidence=0.82,
            pressure_mode=gatekeeper.mode,
            pressure_reasons=gatekeeper.reasons,
        )

    def _merge_entities(
        self,
        draft: ReservationDraft,
        normalized: str,
        *,
        reference: datetime,
        phone_expected: bool = False,
        name_expected: bool = False,
    ) -> None:
        party_size = _extract_party_size(normalized)
        if party_size is not None:
            draft.party_size = party_size
        reservation_date = parse_reservation_date(normalized, reference=reference)
        if reservation_date is not None:
            draft.requested_date = reservation_date.requested_date
            draft.requested_date_text = reservation_date.display_text
            draft.date_parser = reservation_date.parser
        reservation_time = parse_reservation_time(
            normalized,
            reference=reference,
            preferred_date=draft.requested_date,
        )
        if reservation_time is not None:
            draft.requested_at = reservation_time.requested_at
            draft.requested_time_text = reservation_time.display_text
            draft.time_parser = reservation_time.parser
        customer_name = _extract_customer_name(
            normalized,
            name_expected=name_expected,
            spelling_expected=draft.customer_name_spelling_requested,
        )
        if customer_name is not None:
            if draft.customer_name != customer_name:
                draft.customer_name_confirmed = False
            draft.customer_name = customer_name
        phone = _extract_phone(normalized, phone_expected=phone_expected)
        if phone is not None:
            draft.phone = phone

    def _detect_intent(self, normalized: str, call: VoiceCall) -> VoiceIntent:
        if any(
            phrase in normalized
            for phrase in (
                "encargado",
                "responsable",
                "hablar con alguien",
                "hablar con una persona",
                "pasame con alguien",
            )
        ):
            return VoiceIntent.SPEAK_TO_MANAGER
        if any(word in normalized for word in ("cancelar", "anular", "cancelacion")):
            return VoiceIntent.CANCEL_RESERVATION
        if any(word in normalized for word in ("cambiar", "modificar", "mover")):
            return VoiceIntent.MODIFY_RESERVATION
        if any(word in normalized for word in ("llegado", "llegamos", "hemos llegado")):
            return VoiceIntent.CONFIRM_ARRIVAL
        if any(word in normalized for word in ("hay sitio", "disponibilidad", "teneis mesa")):
            return VoiceIntent.CHECK_AVAILABILITY
        if any(
            word in normalized
            for word in (
                "reserv",
                "mesa para",
                "queria mesa",
                "hacer una reserva",
                "hacer reserva",
            )
        ):
            return VoiceIntent.CREATE_RESERVATION
        if call.intent is not VoiceIntent.UNKNOWN:
            return call.intent
        return VoiceIntent.UNKNOWN

    def _handle_scenario(self, call: VoiceCall, scenario: VoiceScenario) -> VoiceTurnResult:
        call.intent = scenario.intent
        call.scenario_id = scenario.scenario_id
        if scenario.requires_manager:
            return self._escalate(
                call,
                reason=f"scenario:{scenario.scenario_id}",
                reply_text=scenario.reply_text,
                extra_payload={
                    "scenario_id": scenario.scenario_id,
                    "scenario_label": scenario.label,
                    "risk": scenario.risk,
                },
            )
        return VoiceTurnResult(
            call=call,
            reply_text=scenario.reply_text,
            intent=scenario.intent,
            confidence=0.78,
            action_name=f"utter_{scenario.scenario_id}",
            action_payload={
                "scenario_id": scenario.scenario_id,
                "scenario_label": scenario.label,
                "risk": scenario.risk,
            },
        )

    def _missing_reservation_fields(self, draft: ReservationDraft) -> tuple[str, ...]:
        missing: list[str] = []
        if draft.party_size is None:
            missing.append("party_size")
        if draft.requested_time_text is None:
            missing.append("requested_time_text")
        if draft.customer_name is None:
            missing.append("customer_name")
        if draft.phone is None:
            missing.append("phone")
        return tuple(missing)

    def _missing_cancel_fields(self, draft: ReservationDraft) -> tuple[str, ...]:
        if draft.phone is None and draft.customer_name is None:
            return ("phone_or_customer_name",)
        return ()

    def _find_reservation(self, draft: ReservationDraft) -> VoiceReservation | None:
        candidates = [
            reservation
            for reservation in self.reservations.values()
            if reservation.status is VoiceReservationStatus.CONFIRMED
        ]
        if draft.phone is not None:
            for reservation in candidates:
                if reservation.phone == draft.phone:
                    return reservation
        if draft.customer_name is not None:
            target_name = _normalize_text(draft.customer_name)
            for reservation in candidates:
                if _normalize_text(reservation.customer_name) == target_name:
                    return reservation
        return None

    def _question_for_missing_field(self, field: str) -> str:
        if field == "party_size":
            return "Para cuantas personas seria?"
        if field == "requested_time_text":
            return "A que hora le gustaria la reserva?"
        if field == "customer_name":
            return "A que nombre dejamos la reserva?"
        if field == "phone":
            return "Me confirma un telefono de contacto?"
        return "Me indica el nombre o telefono de la reserva?"

    def _action_for_missing_field(self, field: str) -> str:
        actions = {
            "party_size": "utter_ask_party_size",
            "requested_time_text": "utter_ask_requested_time",
            "customer_name": "utter_ask_customer_name",
            "phone": "utter_ask_phone",
            "phone_or_customer_name": "utter_ask_reservation_identifier",
            "intent": "utter_ask_intent",
        }
        return actions.get(field, "utter_ask_clarification")

    def _escalate(
        self,
        call: VoiceCall,
        *,
        reason: str,
        reply_text: str,
        availability: AvailabilityResult | None = None,
        extra_payload: dict[str, object] | None = None,
    ) -> VoiceTurnResult:
        call.status = VoiceCallStatus.ESCALATED
        call.escalated_reason = reason
        payload = {
            "source_call_id": call.call_id,
            "intent": call.intent.value,
            "reason": reason,
            "scenario_id": call.scenario_id,
            "pressure_mode": availability.pressure_mode if availability is not None else None,
            "pressure_reasons": (
                list(availability.pressure_reasons) if availability is not None else []
            ),
        }
        if extra_payload:
            payload.update(extra_payload)
        self.restaurant_service.record_operational_action(
            action_type="voice_call_escalated",
            target_channel="shared_panel",
            message=f"Llamada escalada al encargado: {reason}",
            payload=payload,
        )
        return VoiceTurnResult(
            call=call,
            reply_text=reply_text,
            intent=call.intent,
            confidence=1.0,
            action_name="action_escalate_to_manager",
            action_payload={
                "reason": reason,
                "target_channel": "shared_panel",
                "scenario_id": call.scenario_id,
            },
            availability=availability,
            escalated=True,
        )

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip()


def _extract_party_size(normalized: str) -> int | None:
    patterns = [
        r"(?:para|somos|seremos)\s+(\d{1,2})\b",
        r"\b(\d{1,2})\s+(?:personas|pax|comensales)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = int(match.group(1))
            return value if value > 0 else None
    for word, value in _SPANISH_NUMBERS.items():
        if re.search(rf"(?:para|somos|seremos)\s+{word}\b", normalized):
            return value
    return None


def _extract_time_text(normalized: str) -> str | None:
    match = re.search(r"\b([01]?\d|2[0-3])[:.h](\d{2})\b", normalized)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"
    match = re.search(r"\b(?:a las|sobre las|para las)\s+([01]?\d|2[0-3])\b", normalized)
    if match:
        return f"{int(match.group(1)):02d}:00"
    return None


def _extract_customer_name(
    normalized: str,
    *,
    name_expected: bool = False,
    spelling_expected: bool = False,
) -> str | None:
    match = re.search(
        r"(?:a nombre de|nombre de|me llamo|soy)\s+([a-zñ]+(?:\s+[a-zñ]+){0,2})",
        normalized,
    )
    if not match and spelling_expected:
        spelled_name = _extract_spelled_customer_name(normalized)
        if spelled_name is not None:
            return spelled_name
    if not match and name_expected:
        return _extract_expected_name_from_short_reply(normalized)
    if not match:
        return None
    raw = match.group(1)
    cleaned_words = [word for word in raw.split() if word not in _NAME_STOP_WORDS]
    if not cleaned_words:
        return None
    return _format_customer_name(cleaned_words)


def _extract_customer_name_correction(normalized: str) -> str | None:
    spelled_name = _extract_spelled_customer_name(normalized)
    if spelled_name is not None:
        return spelled_name
    matches = tuple(
        re.finditer(
            r"(?:es|seria|se llama|me llamo|a nombre de|nombre de)\s+"
            r"([a-zÃ±]+(?:\s+[a-zÃ±]+){0,2})",
            normalized,
        )
    )
    if not matches:
        return None
    match = matches[-1]
    raw = match.group(1)
    cleaned_words = [word for word in raw.split() if word not in _NAME_STOP_WORDS]
    if not cleaned_words:
        return None
    return _format_customer_name(cleaned_words)


def _detect_name_confirmation(normalized: str) -> bool | None:
    if re.search(
        r"\b(?:no|incorrecto|no es correcto|te has equivocado|se ha equivocado|"
        r"no es mi nombre|ese no es|este no es)\b",
        normalized,
    ):
        return False
    if re.search(
        r"\b(?:si|correcto|exacto|eso es|esta bien|es correcto|vale|de acuerdo)\b",
        normalized,
    ):
        return True
    return None


def _is_customer_name_expected(draft: ReservationDraft) -> bool:
    return (
        draft.customer_name is None
        and draft.party_size is not None
        and draft.requested_time_text is not None
    ) or draft.customer_name_spelling_requested


def _extract_expected_name_from_short_reply(normalized: str) -> str | None:
    if _detect_name_confirmation(normalized) is not None:
        return None
    if _has_phone_context(normalized) or re.search(r"\d", normalized):
        return None
    tokens = [
        token
        for token in re.findall(r"[a-z]+", normalized)
        if token not in _NAME_STOP_WORDS and token not in {"hola", "buenas", "mira"}
    ]
    if not tokens or len(tokens) > 3:
        return None
    return _format_customer_name(tokens)


def _extract_spelled_customer_name(normalized: str) -> str | None:
    text = re.sub(
        r"\b(?:se escribe|deletreado|deletreo|letra a letra|seria|es|nombre)\b",
        " ",
        normalized,
    )
    tokens = re.findall(r"[a-z]+", text)
    letters: list[str] = []
    index = 0
    while index < len(tokens):
        if index + 1 < len(tokens):
            pair = f"{tokens[index]} {tokens[index + 1]}"
            if pair in _SPELLING_LETTERS:
                letters.append(_SPELLING_LETTERS[pair])
                index += 2
                continue
        letter = _SPELLING_LETTERS.get(tokens[index])
        if letter is not None:
            letters.append(letter)
        index += 1
    if len(letters) < 2:
        return None
    return "".join(letters).capitalize()


def _format_customer_name(words: list[str]) -> str:
    cleaned = " ".join(words)
    return _CUSTOMER_NAME_ALIASES.get(
        cleaned,
        " ".join(word.capitalize() for word in words),
    )


def _is_phone_expected_for_reservation(draft: ReservationDraft) -> bool:
    return (
        draft.phone is None
        and draft.party_size is not None
        and draft.requested_time_text is not None
        and draft.customer_name is not None
        and draft.customer_name_confirmed
    )


def _extract_phone(normalized: str, *, phone_expected: bool = False) -> str | None:
    for match in re.finditer(r"(?<!\d)(?:\+?\d[\d\s.-]{5,}\d)(?!\d)", normalized):
        phone = _normalize_phone(match.group(0))
        if _is_acceptable_phone(phone, focused=phone_expected or _has_phone_context(normalized)):
            return phone

    focused_segments = _phone_focused_segments(normalized)
    for segment in focused_segments:
        spoken_phone = _extract_spoken_phone(segment)
        if spoken_phone is not None and _is_acceptable_phone(spoken_phone, focused=True):
            return spoken_phone

    if phone_expected:
        spoken_phone = _extract_spoken_phone(normalized)
        if spoken_phone is not None and _is_acceptable_phone(spoken_phone, focused=True):
            return spoken_phone
    return None


def _normalize_phone(phone: str) -> str:
    prefix = "+" if phone.strip().startswith("+") else ""
    digits = re.sub(r"\D", "", phone)
    return f"{prefix}{digits}" if digits else phone


def _is_acceptable_phone(phone: str, *, focused: bool) -> bool:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 9:
        return True
    return focused and digits.startswith("34") and len(digits) == 11


def _has_phone_context(normalized: str) -> bool:
    return bool(
        re.search(
            r"\b(?:telefono|movil|contacto|numero\s+(?:de\s+)?telefono|numero\s+de\s+contacto)\b",
            normalized,
        )
    )


def _phone_focused_segments(normalized: str) -> list[str]:
    segments: list[str] = []
    trigger_pattern = re.compile(
        r"\b(?:mi\s+)?(?:telefono|movil|contacto|numero\s+(?:de\s+)?telefono|"
        r"numero\s+de\s+contacto)\b"
    )
    stop_pattern = re.compile(
        r"\b(?:a\s+nombre\s+de|nombre\s+de|me\s+llamo|soy|gracias|por\s+favor)\b"
    )
    for match in trigger_pattern.finditer(normalized):
        segment = normalized[match.end() :]
        stop = stop_pattern.search(segment)
        if stop:
            segment = segment[: stop.start()]
        segments.append(segment)
    return segments


def _extract_spoken_phone(text: str) -> str | None:
    tokens = re.findall(r"\d+|[a-zñ]+", text)
    if not tokens:
        return None
    groups: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.isdigit():
            groups.append(token)
            index += 1
            continue

        zero_repeat = _parse_zero_repeat(tokens, index)
        if zero_repeat is not None:
            digits, consumed = zero_repeat
            groups.append(digits)
            index += consumed
            continue

        repeated_digit = _parse_repeated_digit(tokens, index)
        if repeated_digit is not None:
            digits, consumed = repeated_digit
            groups.append(digits)
            index += consumed
            continue

        parsed_number = _parse_spanish_number_group(tokens, index)
        if parsed_number is not None:
            value, consumed = parsed_number
            groups.append(_phone_group_digits(value))
            index += consumed
            continue

        index += 1

    digits = "".join(groups)
    return digits if digits else None


def _parse_zero_repeat(tokens: list[str], index: int) -> tuple[str, int] | None:
    if index + 1 >= len(tokens):
        return None
    amount = _small_count(tokens[index])
    if amount is None or amount < 2 or amount > 4:
        return None
    if tokens[index + 1] not in {"cero", "ceros"}:
        return None
    return "0" * amount, 2


def _parse_repeated_digit(tokens: list[str], index: int) -> tuple[str, int] | None:
    repeat_counts = {"doble": 2, "triple": 3}
    repeat_count = repeat_counts.get(tokens[index])
    if repeat_count is None or index + 1 >= len(tokens):
        return None
    digit = _single_spoken_digit(tokens[index + 1])
    if digit is None:
        return None
    return digit * repeat_count, 2


def _parse_spanish_number_group(tokens: list[str], index: int) -> tuple[int, int] | None:
    token = tokens[index]
    if token in _SPANISH_HUNDREDS:
        value = _SPANISH_HUNDREDS[token]
        consumed = 1
        tail = _parse_spanish_number_under_100(tokens, index + consumed)
        if tail is not None:
            tail_value, tail_consumed = tail
            value += tail_value
            consumed += tail_consumed
        return value, consumed
    return _parse_spanish_number_under_100(tokens, index)


def _parse_spanish_number_under_100(tokens: list[str], index: int) -> tuple[int, int] | None:
    if index >= len(tokens):
        return None
    token = tokens[index]
    digit = _single_spoken_digit(token)
    if digit is not None:
        return int(digit), 1
    if token in _SPANISH_TEENS:
        return _SPANISH_TEENS[token], 1
    if token not in _SPANISH_TENS:
        return None
    value = _SPANISH_TENS[token]
    consumed = 1
    if index + 2 < len(tokens) and tokens[index + 1] == "y":
        unit = _single_spoken_digit(tokens[index + 2])
        if unit is not None:
            value += int(unit)
            consumed = 3
    return value, consumed


def _single_spoken_digit(token: str) -> str | None:
    return _SPANISH_DIGIT_WORDS.get(token)


def _small_count(token: str) -> int | None:
    values = {"dos": 2, "tres": 3, "cuatro": 4}
    return values.get(token)


def _phone_group_digits(value: int) -> str:
    if value < 10:
        return str(value)
    if value < 100:
        return f"{value:02d}"
    if value < 1000:
        return f"{value:03d}"
    return str(value)
