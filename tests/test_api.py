from __future__ import annotations

from datetime import UTC, datetime, timedelta

from apps.api.main import create_app
from fastapi.testclient import TestClient
from services.alerts.anomaly import DurationAnomalyConfig, OperationalAnomalyDetector
from services.events.models import TableSession
from services.events.service import RestaurantMVPService


def make_client() -> TestClient:
    return TestClient(create_app(RestaurantMVPService()))


def test_health_and_catalog_endpoints() -> None:
    client = make_client()

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    tables = client.get("/api/v1/tables")
    assert tables.status_code == 200
    assert len(tables.json()) == 1
    assert tables.json()[0]["state"] == "ready"


def test_catalog_configuration_endpoints_create_operational_topology() -> None:
    client = make_client()

    camera = client.post(
        "/api/v1/cameras",
        json={"camera_id": "camera_02", "name": "Camara 02", "status": "online"},
    )
    assert camera.status_code == 201

    zone = client.post(
        "/api/v1/zones",
        json={
            "zone_id": "zone_table_02",
            "name": "Zona Mesa 02",
            "camera_id": "camera_02",
            "polygon_definition": [[10, 10], [300, 10], [300, 220], [10, 220]],
        },
    )
    assert zone.status_code == 201

    table = client.post(
        "/api/v1/tables",
        json={
            "table_id": "table_02",
            "name": "Mesa 02",
            "capacity": 6,
            "zone_id": "zone_table_02",
            "active": True,
        },
    )
    assert table.status_code == 201
    assert table.json()["state"] == "ready"

    response = client.post(
        "/api/v1/observations",
        json={
            "camera_id": "camera_02",
            "zone_id": "zone_table_02",
            "table_id": "table_02",
            "people_count": 5,
            "confidence": 0.97,
            "observed_at": "2026-04-13T13:00:00Z",
        },
    )
    assert response.status_code == 202
    assert response.json()["table"]["state"] == "occupied"


def test_observation_endpoint_creates_session_and_events() -> None:
    client = make_client()

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


def test_alert_endpoint_lists_operational_duration_alerts() -> None:
    detector = OperationalAnomalyDetector(
        DurationAnomalyConfig(
            min_samples=5,
            z_threshold=2.0,
            min_current_duration_seconds=0,
            min_absolute_margin_seconds=60,
        )
    )
    service = RestaurantMVPService(anomaly_detector=detector)
    history_start = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
    for index in range(5):
        start = history_start + timedelta(days=index)
        service.sessions_by_id[f"ses_history_{index}"] = TableSession(
            session_id=f"ses_history_{index}",
            table_id="table_01",
            start_ts=start,
            end_ts=start + timedelta(minutes=30),
            people_count_initial=2,
            people_count_peak=2,
            final_status="pending_cleaning",
            duration_seconds=1800,
        )
    client = TestClient(create_app(service))

    first = client.post(
        "/api/v1/observations",
        json={
            "camera_id": "camera_mvp_01",
            "zone_id": "zone_table_01",
            "table_id": "table_01",
            "people_count": 2,
            "confidence": 0.98,
            "observed_at": "2026-04-13T12:00:00Z",
        },
    )
    assert first.status_code == 202

    second = client.post(
        "/api/v1/observations",
        json={
            "camera_id": "camera_mvp_01",
            "zone_id": "zone_table_01",
            "table_id": "table_01",
            "people_count": 2,
            "confidence": 0.98,
            "observed_at": "2026-04-13T12:45:00Z",
        },
    )
    assert second.status_code == 202

    alerts = client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    payload = alerts.json()
    assert len(payload) == 1
    assert payload[0]["alert_type"] == "long_session_attention"
    assert payload[0]["severity"] == "warning"
    assert payload[0]["evidence_json"]["elapsed_seconds"] == 2700
