from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_health_and_catalog_endpoints() -> None:
    client = TestClient(create_app())

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    tables = client.get("/api/v1/tables")
    assert tables.status_code == 200
    assert len(tables.json()) == 1
    assert tables.json()[0]["state"] == "ready"


def test_observation_endpoint_creates_session_and_events() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/observations",
        json={
            "camera_id": "camera_mvp_01",
            "zone_id": "zone_table_01",
            "table_id": "table_01",
            "people_count": 3,
            "confidence": 0.98,
            "observed_at": "2026-04-13T12:00:00Z",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["table"]["state"] == "occupied"
    assert payload["session"]["table_id"] == "table_01"
    assert len(payload["events"]) >= 4

    events = client.get("/api/v1/events")
    assert events.status_code == 200
    assert len(events.json()) >= 4
