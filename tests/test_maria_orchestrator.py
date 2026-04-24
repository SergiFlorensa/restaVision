from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.alerts.anomaly import AlertSeverity, OperationalAlert, OperationalAlertType
from services.events.models import DomainEvent, EventType
from services.maria.orchestrator import MariaOrchestrator, MariaTriggerReason
from services.proxemics.engine import CrowdingAssessment, CrowdingLevel


def make_event(event_type: EventType, at: datetime) -> DomainEvent:
    return DomainEvent(
        event_id=f"evt_{event_type.value}",
        ts=at,
        camera_id="camera_mvp_01",
        zone_id="zone_table_01",
        table_id="table_01",
        event_type=event_type,
        confidence=0.9,
        payload_json={},
    )


def test_orchestrator_prioritizes_operator_query() -> None:
    orchestrator = MariaOrchestrator()
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)

    request = orchestrator.build_request(
        now=now,
        events=[],
        explicit_query="Maria resume el estado de sala",
    )

    assert request.should_run is True
    assert request.reason is MariaTriggerReason.OPERATOR_QUERY
    assert "operador" in request.user_prompt


def test_orchestrator_triggers_on_low_confidence_event_with_cooldown() -> None:
    orchestrator = MariaOrchestrator()
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)
    events = [make_event(EventType.LOW_CONFIDENCE_OBSERVATION, now)]

    first = orchestrator.build_request(now=now, events=events)
    second = orchestrator.build_request(now=now + timedelta(seconds=10), events=events)
    third = orchestrator.build_request(now=now + timedelta(seconds=50), events=events)

    assert first.should_run is True
    assert first.reason is MariaTriggerReason.LOW_CONFIDENCE
    assert second.should_run is False
    assert third.should_run is True


def test_orchestrator_uses_warning_alert_when_no_critical_event() -> None:
    orchestrator = MariaOrchestrator()
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)
    warning_alert = OperationalAlert(
        alert_id="alert_1",
        ts=now,
        table_id="table_01",
        session_id="ses_01",
        alert_type=OperationalAlertType.LONG_SESSION_ATTENTION,
        severity=AlertSeverity.WARNING,
        message="mesa fuera de rango",
        score=0.8,
        evidence_json={},
    )

    request = orchestrator.build_request(now=now, events=[], alerts=[warning_alert])

    assert request.should_run is True
    assert request.reason is MariaTriggerReason.OPERATIONAL_ALERT
    assert request.table_id == "table_01"


def test_orchestrator_uses_high_crowding_when_available() -> None:
    orchestrator = MariaOrchestrator()
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)
    crowding = CrowdingAssessment(
        area_id="barra",
        person_count=7,
        area_m2=10.0,
        density_people_per_m2=0.7,
        level=CrowdingLevel.HIGH,
        explanation="densidad alta",
    )

    request = orchestrator.build_request(now=now, events=[], crowding=[crowding])

    assert request.should_run is True
    assert request.reason is MariaTriggerReason.CROWDING_HIGH
    assert request.zone_id == "barra"


def test_orchestrator_falls_back_to_periodic_summary() -> None:
    orchestrator = MariaOrchestrator()
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)

    first = orchestrator.build_request(now=now, events=[])
    second = orchestrator.build_request(now=now + timedelta(minutes=2), events=[])
    third = orchestrator.build_request(now=now + timedelta(minutes=11), events=[])

    assert first.reason is MariaTriggerReason.PERIODIC_SUMMARY
    assert first.should_run is True
    assert second.should_run is False
    assert third.should_run is True
