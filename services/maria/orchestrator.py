from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum

from services.alerts.anomaly import AlertSeverity, OperationalAlert
from services.events.models import DomainEvent, EventType
from services.proxemics.engine import CrowdingAssessment, CrowdingLevel


class MariaTriggerPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class MariaTriggerReason(StrEnum):
    OPERATOR_QUERY = "operator_query"
    LOW_CONFIDENCE = "low_confidence"
    TABLE_TRANSITION = "table_transition"
    OPERATIONAL_ALERT = "operational_alert"
    CROWDING_HIGH = "crowding_high"
    PERIODIC_SUMMARY = "periodic_summary"


@dataclass(frozen=True, slots=True)
class MariaPromptRequest:
    should_run: bool
    reason: MariaTriggerReason
    priority: MariaTriggerPriority
    user_prompt: str
    table_id: str | None = None
    zone_id: str | None = None
    camera_id: str | None = None


@dataclass(slots=True)
class MariaOrchestratorConfig:
    periodic_interval_seconds: int = 600
    cooldown_operator_query_seconds: int = 5
    cooldown_low_confidence_seconds: int = 45
    cooldown_table_transition_seconds: int = 60
    cooldown_operational_alert_seconds: int = 180
    cooldown_crowding_high_seconds: int = 180
    cooldown_periodic_summary_seconds: int = 600
    max_events_window: int = 30

    def cooldown_for(self, reason: MariaTriggerReason) -> int:
        if reason is MariaTriggerReason.OPERATOR_QUERY:
            return self.cooldown_operator_query_seconds
        if reason is MariaTriggerReason.LOW_CONFIDENCE:
            return self.cooldown_low_confidence_seconds
        if reason is MariaTriggerReason.TABLE_TRANSITION:
            return self.cooldown_table_transition_seconds
        if reason is MariaTriggerReason.OPERATIONAL_ALERT:
            return self.cooldown_operational_alert_seconds
        if reason is MariaTriggerReason.CROWDING_HIGH:
            return self.cooldown_crowding_high_seconds
        return self.cooldown_periodic_summary_seconds


class MariaOrchestrator:
    """Triggers multimodal analysis only when useful for local hardware budgets."""

    def __init__(self, config: MariaOrchestratorConfig | None = None) -> None:
        self.config = config or MariaOrchestratorConfig()
        self._last_requested_at_by_reason: dict[MariaTriggerReason, datetime] = {}

    def build_request(
        self,
        now: datetime,
        events: list[DomainEvent],
        alerts: list[OperationalAlert] | None = None,
        crowding: list[CrowdingAssessment] | None = None,
        explicit_query: str | None = None,
    ) -> MariaPromptRequest:
        compact_events = list(reversed(events[-self.config.max_events_window :]))
        alerts = alerts or []
        crowding = crowding or []

        if explicit_query is not None and explicit_query.strip():
            return self._request_with_cooldown(
                now=now,
                reason=MariaTriggerReason.OPERATOR_QUERY,
                priority=MariaTriggerPriority.HIGH,
                prompt=f"Responder consulta del operador: {explicit_query.strip()}",
            )

        for event in compact_events:
            if event.event_type is EventType.LOW_CONFIDENCE_OBSERVATION:
                return self._request_with_cooldown(
                    now=now,
                    reason=MariaTriggerReason.LOW_CONFIDENCE,
                    priority=MariaTriggerPriority.HIGH,
                    prompt=(
                        "Revisar captura por observacion de baja confianza. "
                        "Confirmar ocupacion real y sugerir accion operativa."
                    ),
                    table_id=event.table_id,
                    zone_id=event.zone_id,
                    camera_id=event.camera_id,
                )
            if event.event_type in {
                EventType.TABLE_OCCUPIED,
                EventType.TABLE_RELEASED,
                EventType.TABLE_PENDING_CLEANING,
            }:
                return self._request_with_cooldown(
                    now=now,
                    reason=MariaTriggerReason.TABLE_TRANSITION,
                    priority=MariaTriggerPriority.MEDIUM,
                    prompt=(
                        "Resumir transicion de mesa detectada y confirmar si "
                        "el estado operativo es coherente."
                    ),
                    table_id=event.table_id,
                    zone_id=event.zone_id,
                    camera_id=event.camera_id,
                )

        for alert in reversed(alerts):
            if alert.severity is AlertSeverity.WARNING:
                return self._request_with_cooldown(
                    now=now,
                    reason=MariaTriggerReason.OPERATIONAL_ALERT,
                    priority=MariaTriggerPriority.MEDIUM,
                    prompt=(
                        "Validar alerta operativa de duracion de sesion y "
                        "proponer siguiente accion de sala."
                    ),
                    table_id=alert.table_id,
                )

        for zone_assessment in crowding:
            if zone_assessment.level is CrowdingLevel.HIGH:
                return self._request_with_cooldown(
                    now=now,
                    reason=MariaTriggerReason.CROWDING_HIGH,
                    priority=MariaTriggerPriority.MEDIUM,
                    prompt=(
                        "Analizar congestion de zona y priorizar recomendaciones "
                        "operativas para reducir saturacion."
                    ),
                    zone_id=zone_assessment.area_id,
                )

        return self._request_with_cooldown(
            now=now,
            reason=MariaTriggerReason.PERIODIC_SUMMARY,
            priority=MariaTriggerPriority.LOW,
            prompt=(
                "Generar resumen breve del estado de sala con foco en mesas que requieran atencion."
            ),
        )

    def _request_with_cooldown(
        self,
        now: datetime,
        reason: MariaTriggerReason,
        priority: MariaTriggerPriority,
        prompt: str,
        table_id: str | None = None,
        zone_id: str | None = None,
        camera_id: str | None = None,
    ) -> MariaPromptRequest:
        if self._is_in_cooldown(reason=reason, now=now):
            return MariaPromptRequest(
                should_run=False,
                reason=reason,
                priority=priority,
                user_prompt=prompt,
                table_id=table_id,
                zone_id=zone_id,
                camera_id=camera_id,
            )

        self._last_requested_at_by_reason[reason] = now
        return MariaPromptRequest(
            should_run=True,
            reason=reason,
            priority=priority,
            user_prompt=prompt,
            table_id=table_id,
            zone_id=zone_id,
            camera_id=camera_id,
        )

    def _is_in_cooldown(self, reason: MariaTriggerReason, now: datetime) -> bool:
        last_at = self._last_requested_at_by_reason.get(reason)
        if last_at is None:
            return False
        elapsed = (now - last_at).total_seconds()
        return elapsed < self.config.cooldown_for(reason)
