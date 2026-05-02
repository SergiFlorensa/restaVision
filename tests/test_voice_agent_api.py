from __future__ import annotations

from apps.api.main import create_app
from fastapi.testclient import TestClient
from services.events.service import RestaurantMVPService


def make_client() -> TestClient:
    return TestClient(create_app(RestaurantMVPService()))


def test_voice_agent_confirms_reservation_against_ready_table() -> None:
    client = make_client()

    call = client.post(
        "/api/v1/voice/calls",
        json={"caller_phone": "600 123 123", "source_channel": "browser_simulator"},
    )
    assert call.status_code == 201
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 4 a las 21:30 "
                "a nombre de Sergio, mi telefono es 600123123"
            ),
            "confidence": 0.92,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["intent"] == "create_reservation"
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["party_size"] == 4
    assert payload["reservation"]["requested_time_text"] == "02/05/2026 21:30"
    assert payload["reservation"]["requested_at"].startswith("2026-05-02T21:30:00")
    assert payload["reservation"]["customer_name"] == "Sergio"
    assert payload["reservation"]["table_id"] == "table_01"
    assert payload["availability"]["available"] is True
    assert payload["action_name"] == "action_confirm_reservation"
    assert payload["call"]["scenario_id"] is None
    assert "el 2 de mayo a las 21:30" in payload["reply_text"]

    reservations = client.get("/api/v1/voice/reservations")
    assert reservations.status_code == 200
    assert reservations.json()[0]["reservation_id"] == payload["reservation"]["reservation_id"]


def test_voice_agent_rejects_auto_reservation_when_no_ready_table() -> None:
    client = make_client()
    runtime = client.patch(
        "/api/v1/tables/table_01/runtime",
        json={"state": "occupied", "phase": "eating", "people_count": 4},
    )
    assert runtime.status_code == 200
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Quiero reservar mesa para 4 a las 22:00 a nombre de Laura telefono 611222333"
            ),
            "confidence": 0.9,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["call"]["status"] == "rejected"
    assert payload["availability"]["available"] is False
    assert payload["availability"]["reason"] == "no_ready_table_for_party_size"


def test_voice_agent_normalizes_relative_spanish_reservation_time() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 3 mañana a las nueve y media "
                "a nombre de Carla telefono 644555666"
            ),
            "confidence": 0.91,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["requested_time_text"] == "03/05/2026 21:30"
    assert payload["reservation"]["requested_at"].startswith("2026-05-03T21:30:00")
    assert payload["call"]["reservation_draft"]["time_parser"] in {
        "manual_spanish",
        "dateparser",
    }


def test_voice_agent_keeps_partial_date_and_combines_later_time() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 3 el viernes a nombre de Carla telefono 644555666"
            ),
            "confidence": 0.91,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert first_turn.status_code == 200
    first_payload = first_turn.json()
    assert first_payload["missing_fields"] == ["requested_time_text"]
    assert first_payload["action_name"] == "utter_ask_requested_time"
    assert first_payload["call"]["reservation_draft"]["requested_date_text"] == "08/05/2026"
    assert first_payload["call"]["reservation_draft"]["requested_time_text"] is None

    second_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": "a las nueve y media",
            "confidence": 0.92,
            "observed_at": "2026-05-02T19:01:00+02:00",
        },
    )

    assert second_turn.status_code == 200
    second_payload = second_turn.json()
    assert second_payload["call"]["status"] == "confirmed"
    assert second_payload["action_name"] == "action_confirm_reservation"
    assert second_payload["reservation"]["requested_time_text"] == "08/05/2026 21:30"
    assert second_payload["reservation"]["requested_at"].startswith("2026-05-08T21:30:00")


def test_voice_agent_cancels_existing_reservation_by_phone() -> None:
    client = make_client()
    create_call = client.post("/api/v1/voice/calls", json={})
    create_call_id = create_call.json()["call_id"]
    created = client.post(
        f"/api/v1/voice/calls/{create_call_id}/turns",
        json={
            "transcript": ("Reserva para dos a las 20:30 a nombre de Marta telefono 622333444"),
            "confidence": 0.94,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )
    assert created.status_code == 200
    reservation_id = created.json()["reservation"]["reservation_id"]

    cancel_call = client.post("/api/v1/voice/calls", json={})
    cancel_call_id = cancel_call.json()["call_id"]
    cancelled = client.post(
        f"/api/v1/voice/calls/{cancel_call_id}/turns",
        json={"transcript": "Quiero cancelar mi reserva, telefono 622333444"},
    )

    assert cancelled.status_code == 200
    payload = cancelled.json()
    assert payload["intent"] == "cancel_reservation"
    assert payload["call"]["status"] == "closed"
    assert payload["reservation"]["reservation_id"] == reservation_id
    assert payload["reservation"]["status"] == "cancelled"


def test_voice_agent_escalates_low_confidence_transcript() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={"transcript": "ruido de llamada", "confidence": 0.3},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["escalated"] is True
    assert payload["action_name"] == "action_escalate_to_manager"
    assert payload["call"]["status"] == "escalated"
    assert payload["call"]["escalated_reason"] == "low_stt_confidence"


def test_voice_agent_routes_information_scenario_to_manager() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={"transcript": "Hola, queria saber el horario de cocina"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["intent"] == "information_request"
    assert payload["escalated"] is True
    assert payload["call"]["scenario_id"] == "opening_hours"
    assert payload["call"]["escalated_reason"] == "scenario:opening_hours"
    assert payload["action_name"] == "action_escalate_to_manager"


def test_voice_agent_interrupts_reservation_for_allergen_scenario() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 2 manana a las 21:00 "
                "a nombre de Ana telefono 655111222, soy celiaco"
            ),
            "confidence": 0.95,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["intent"] == "special_request"
    assert payload["escalated"] is True
    assert payload["call"]["scenario_id"] == "allergens"
    assert payload["reservation"] is None
    assert payload["action_payload"]["scenario_id"] == "allergens"


def test_voice_gatekeeper_escalates_when_physical_queue_creates_pressure() -> None:
    client = make_client()
    for party_size in (2, 3):
        group = client.post("/api/v1/queue/groups", json={"party_size": party_size})
        assert group.status_code == 201

    status = client.get("/api/v1/voice/gatekeeper/status")
    assert status.status_code == 200
    assert status.json()["mode"] == "guarded"
    assert "physical_queue_waiting" in status.json()["reasons"]

    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]
    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 2 a las 21:00 a nombre de Pablo telefono 633444555"
            ),
            "confidence": 0.93,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["escalated"] is True
    assert payload["call"]["status"] == "escalated"
    assert payload["call"]["escalated_reason"] == "service_pressure_overflow"
    assert payload["availability"]["available"] is False
    assert payload["availability"]["reason"] == "service_pressure_overflow"
    assert payload["availability"]["pressure_mode"] == "guarded"
    assert payload["action_payload"]["reason"] == "service_pressure_overflow"


def test_voice_metrics_report_resolution_and_gatekeeper_state() -> None:
    client = make_client()
    confirmed_call = client.post("/api/v1/voice/calls", json={})
    confirmed_call_id = confirmed_call.json()["call_id"]
    confirmed = client.post(
        f"/api/v1/voice/calls/{confirmed_call_id}/turns",
        json={
            "transcript": ("Reserva para dos a las 20:30 a nombre de Marta telefono 622333444"),
            "confidence": 0.94,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )
    assert confirmed.status_code == 200

    escalated_call = client.post("/api/v1/voice/calls", json={})
    escalated_call_id = escalated_call.json()["call_id"]
    escalated = client.post(
        f"/api/v1/voice/calls/{escalated_call_id}/turns",
        json={"transcript": "ruido", "confidence": 0.2},
    )
    assert escalated.status_code == 200

    metrics = client.get("/api/v1/voice/metrics")

    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["total_calls"] == 2
    assert payload["confirmed_calls"] == 1
    assert payload["escalated_calls"] == 1
    assert payload["total_reservations"] == 1
    assert payload["confirmed_reservations"] == 1
    assert payload["auto_resolution_rate"] == 0.5
    assert payload["escalation_rate"] == 0.5
    assert payload["average_turns_per_call"] == 1.0
    assert payload["gatekeeper"]["mode"] in {"normal", "guarded", "critical"}
