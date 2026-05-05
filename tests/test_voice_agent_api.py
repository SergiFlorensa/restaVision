from __future__ import annotations

from apps.api.main import create_app
from fastapi.testclient import TestClient
from services.events.service import RestaurantMVPService
from services.voice.evaluation import evaluate_voice_agent_baseline


def make_client() -> TestClient:
    return TestClient(create_app(RestaurantMVPService()))


def post_turn(
    client: TestClient,
    call_id: str,
    transcript: str,
    *,
    confidence: float = 0.95,
    observed_at: str = "2026-05-02T19:00:00+02:00",
) -> dict:
    response = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": transcript,
            "confidence": confidence,
            "observed_at": observed_at,
        },
    )
    assert response.status_code == 200
    return response.json()


def confirm_customer_name(client: TestClient, call_id: str) -> dict:
    return post_turn(
        client,
        call_id,
        "si correcto",
        observed_at="2026-05-02T19:01:00+02:00",
    )


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
    assert payload["action_name"] == "utter_confirm_customer_name"
    assert payload["missing_fields"] == ["customer_name_confirmation"]
    payload = confirm_customer_name(client, call_id)
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
    assert payload["action_name"] == "utter_confirm_customer_name"
    payload = confirm_customer_name(client, call_id)
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
    assert payload["action_name"] == "utter_confirm_customer_name"
    payload = confirm_customer_name(client, call_id)
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
    assert first_payload["missing_fields"] == ["customer_name_confirmation"]
    assert first_payload["action_name"] == "utter_confirm_customer_name"
    assert first_payload["call"]["reservation_draft"]["requested_date_text"] == "08/05/2026"
    assert first_payload["call"]["reservation_draft"]["requested_time_text"] is None

    name_confirmation = confirm_customer_name(client, call_id)
    assert name_confirmation["missing_fields"] == ["requested_time_text"]
    assert name_confirmation["action_name"] == "utter_ask_requested_time"

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
    assert created.json()["action_name"] == "utter_confirm_customer_name"
    confirmed = confirm_customer_name(client, create_call_id)
    reservation_id = confirmed["reservation"]["reservation_id"]

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


def test_voice_agent_handles_vosk_like_reservation_phrasing() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "hola buenas mira queria hacer una reserva para dos a los nueve a nombre de lara"
            ),
            "confidence": 0.82,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["intent"] == "create_reservation"
    assert payload["action_name"] == "utter_confirm_customer_name"
    assert payload["missing_fields"] == ["customer_name_confirmation"]
    assert payload["call"]["reservation_draft"]["party_size"] == 2
    assert payload["call"]["reservation_draft"]["requested_time_text"] == "02/05/2026 21:00"
    assert payload["call"]["reservation_draft"]["customer_name"] == "Lara"


def test_voice_agent_corrects_common_asr_name_alias_for_sergi() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 2 a las 21:00 a nombre de seres y telefono 666000666"
            ),
            "confidence": 0.9,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["action_name"] == "utter_confirm_customer_name"
    assert payload["call"]["reservation_draft"]["customer_name"] == "Sergi"
    assert "Sergi" in payload["reply_text"]
    payload = confirm_customer_name(client, call_id)
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["customer_name"] == "Sergi"


def test_voice_agent_reasks_name_when_customer_rejects_confirmation() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_payload = post_turn(
        client,
        call_id,
        ("Queria reservar mesa para 2 a las 21:00 a nombre de Seres y telefono 666000666"),
        confidence=0.9,
    )
    assert first_payload["action_name"] == "utter_confirm_customer_name"
    assert first_payload["call"]["reservation_draft"]["customer_name"] == "Sergi"

    rejected_name = post_turn(
        client,
        call_id,
        "no, te has equivocado",
        observed_at="2026-05-02T19:01:00+02:00",
    )
    assert rejected_name["action_name"] == "utter_ask_customer_name"
    assert rejected_name["call"]["reservation_draft"]["customer_name"] is None

    corrected_name = post_turn(
        client,
        call_id,
        "a nombre de Marc",
        observed_at="2026-05-02T19:02:00+02:00",
    )
    assert corrected_name["action_name"] == "utter_confirm_customer_name"
    assert corrected_name["call"]["reservation_draft"]["customer_name"] == "Marc"

    confirmed = post_turn(
        client,
        call_id,
        "si correcto",
        observed_at="2026-05-02T19:03:00+02:00",
    )
    assert confirmed["call"]["status"] == "confirmed"
    assert confirmed["reservation"]["customer_name"] == "Marc"


def test_voice_agent_accepts_short_name_reply_when_name_is_expected() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_payload = post_turn(
        client,
        call_id,
        "Queria reservar mesa para 2 a las 21:00",
        confidence=0.9,
    )
    assert first_payload["action_name"] == "utter_ask_customer_name"

    name_payload = post_turn(
        client,
        call_id,
        "Sergi",
        observed_at="2026-05-02T19:01:00+02:00",
    )
    assert name_payload["action_name"] == "utter_confirm_customer_name"
    assert name_payload["call"]["reservation_draft"]["customer_name"] == "Sergi"


def test_voice_agent_accepts_spelled_foreign_name_after_rejection() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_payload = post_turn(
        client,
        call_id,
        ("Queria reservar mesa para 2 a las 21:00 a nombre de yon telefono 666000666"),
        confidence=0.9,
    )
    assert first_payload["action_name"] == "utter_confirm_customer_name"

    rejected_name = post_turn(
        client,
        call_id,
        "no, no es correcto",
        observed_at="2026-05-02T19:01:00+02:00",
    )
    assert rejected_name["action_name"] == "utter_ask_customer_name"

    spelled_name = post_turn(
        client,
        call_id,
        "jota o hache ene",
        observed_at="2026-05-02T19:02:00+02:00",
    )
    assert spelled_name["action_name"] == "utter_confirm_customer_name"
    assert spelled_name["call"]["reservation_draft"]["customer_name"] == "John"

    confirmed = post_turn(
        client,
        call_id,
        "si correcto",
        observed_at="2026-05-02T19:03:00+02:00",
    )
    assert confirmed["call"]["status"] == "confirmed"
    assert confirmed["reservation"]["customer_name"] == "John"


def test_voice_agent_rejects_short_standalone_spoken_phone_after_prompt() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "hola buenas queria hacer una reserva para dos a los nueve a nombre de lara"
            ),
            "confidence": 0.82,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )
    assert first_turn.status_code == 200
    assert first_turn.json()["action_name"] == "utter_confirm_customer_name"
    first_confirmed = confirm_customer_name(client, call_id)
    assert first_confirmed["action_name"] == "utter_ask_phone"

    second_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": "seis seis seis seis seis seis seis",
            "confidence": 0.9,
            "observed_at": "2026-05-02T19:01:00+02:00",
        },
    )

    assert second_turn.status_code == 200
    payload = second_turn.json()
    assert payload["call"]["status"] == "collecting_details"
    assert payload["action_name"] == "utter_ask_phone"
    assert payload["missing_fields"] == ["phone"]


def test_voice_agent_accepts_nine_digit_standalone_spoken_phone_after_prompt() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    first_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "hola buenas queria hacer una reserva para dos a los nueve a nombre de lara"
            ),
            "confidence": 0.82,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )
    assert first_turn.status_code == 200
    assert first_turn.json()["action_name"] == "utter_confirm_customer_name"
    first_confirmed = confirm_customer_name(client, call_id)
    assert first_confirmed["action_name"] == "utter_ask_phone"

    second_turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": "seis seis seis cero cero cero seis seis seis",
            "confidence": 0.9,
            "observed_at": "2026-05-02T19:01:00+02:00",
        },
    )

    assert second_turn.status_code == 200
    payload = second_turn.json()
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["phone"] == "666000666"
    expected_reply = "Muchas gracias, le esperamos en la Piemontesa de Passeig de Prim."
    assert expected_reply in payload["reply_text"]


def test_voice_agent_extracts_spoken_phone_words_in_full_reservation() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Queria reservar mesa para 2 a las 21:00 a nombre de Lara "
                "telefono seis seis seis cero cero cero seis seis seis"
            ),
            "confidence": 0.91,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["action_name"] == "utter_confirm_customer_name"
    payload = confirm_customer_name(client, call_id)
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["phone"] == "666000666"


def test_voice_agent_extracts_phone_from_natural_contact_phrase() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={
            "transcript": (
                "Si mira el telefono es 600000660, reserva para dos a las 21:00 a nombre de Sergio"
            ),
            "confidence": 0.91,
            "observed_at": "2026-05-02T19:00:00+02:00",
        },
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["action_name"] == "utter_confirm_customer_name"
    payload = confirm_customer_name(client, call_id)
    assert payload["call"]["status"] == "confirmed"
    assert payload["reservation"]["phone"] == "600000660"


def test_voice_agent_handles_vosk_like_opening_hours_question() -> None:
    client = make_client()
    call = client.post("/api/v1/voice/calls", json={})
    call_id = call.json()["call_id"]

    turn = client.post(
        f"/api/v1/voice/calls/{call_id}/turns",
        json={"transcript": "hola buenas queria saber hasta que hora esta abierta la cocina"},
    )

    assert turn.status_code == 200
    payload = turn.json()
    assert payload["intent"] == "information_request"
    assert payload["call"]["scenario_id"] == "opening_hours"
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
    assert payload["action_name"] == "utter_confirm_customer_name"
    payload = confirm_customer_name(client, call_id)
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
    assert confirmed.json()["action_name"] == "utter_confirm_customer_name"
    confirmed = client.post(
        f"/api/v1/voice/calls/{confirmed_call_id}/turns",
        json={
            "transcript": "si correcto",
            "confidence": 0.95,
            "observed_at": "2026-05-02T19:01:00+02:00",
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
    assert payload["average_turns_per_call"] == 1.5
    assert payload["gatekeeper"]["mode"] in {"normal", "guarded", "critical"}


def test_voice_agent_baseline_evaluation_reports_actionable_metrics() -> None:
    report = evaluate_voice_agent_baseline()

    assert report.sample_count >= 8
    assert report.intent_accuracy >= 0.9
    assert report.intent_macro_f1 >= 0.9
    assert report.action_accuracy >= 0.9
    assert report.slot_field_accuracy >= 0.9
    assert report.escalation_accuracy == 1.0
    assert "create_reservation" in report.per_intent
    assert "create_full_reservation" not in report.failed_case_ids


def test_voice_agent_baseline_evaluation_endpoint() -> None:
    client = make_client()

    response = client.get("/api/v1/voice/evaluation/baseline")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sample_count"] >= 8
    assert payload["intent_accuracy"] >= 0.9
    assert payload["action_accuracy"] >= 0.9
    assert payload["slot_field_accuracy"] >= 0.9
    assert payload["escalation_accuracy"] == 1.0
    assert payload["cases"]
    assert payload["cases"][0]["case_id"] == "create_full_reservation"
