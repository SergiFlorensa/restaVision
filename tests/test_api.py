from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import apps.api.main as api_main
from apps.api.main import CameraSnapshot, create_app
from fastapi.testclient import TestClient
from services.alerts.anomaly import DurationAnomalyConfig, OperationalAnomalyDetector
from services.events.models import TableSession
from services.events.service import RestaurantMVPService
from services.vision.geometry import BoundingBox, ScoredDetection
from services.vision.table_service_monitor import TableServiceMonitor, TableServiceMonitorConfig


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


def test_demo_person_detection_status_endpoint_exposes_stream_url() -> None:
    client = make_client()

    response = client.get("/api/v1/demo/person-detection/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is True
    assert payload["stream_url"].startswith("/api/v1/demo/person-detection/stream")
    assert "no identifica" in payload["privacy_note"]


def test_camera_snapshot_endpoint_returns_saved_reference_path(monkeypatch) -> None:
    client = make_client()

    def fake_capture_camera_snapshot(
        source,
        width,
        height,
        output_dir,
        captured_at,
    ) -> CameraSnapshot:
        assert source == 0
        assert width == 640
        assert height == 480
        assert output_dir == Path("data/calibration/snapshots")
        return CameraSnapshot(
            path=output_dir / "snapshot_0_20260424_120000.jpg",
            width=640,
            height=480,
        )

    monkeypatch.setattr(api_main, "_capture_camera_snapshot", fake_capture_camera_snapshot)

    response = client.post("/api/v1/demo/camera-snapshot?source=0")

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved"] is True
    assert payload["camera_source"] == "0"
    assert payload["width"] == 640
    assert payload["height"] == 480
    assert payload["snapshot_path"].endswith("snapshot_0_20260424_120000.jpg")
    assert "ROI" in payload["usage_note"]


def test_camera_snapshot_endpoint_reports_camera_errors(monkeypatch) -> None:
    client = make_client()

    def fake_capture_camera_snapshot(*args, **kwargs) -> CameraSnapshot:
        raise RuntimeError("Could not open video source: 99")

    monkeypatch.setattr(api_main, "_capture_camera_snapshot", fake_capture_camera_snapshot)

    response = client.post("/api/v1/demo/camera-snapshot?source=99")

    assert response.status_code == 503
    assert "Could not open video source" in response.json()["detail"]


def test_yolo_person_detection_status_endpoint_exposes_optional_detector() -> None:
    client = make_client()

    response = client.get(
        "/api/v1/demo/yolo-person/status?confidence=0.4&iou=0.6&inference_stride=4"
    )

    assert response.status_code == 200
    payload = response.json()
    assert "available" in payload
    assert payload["stream_url"].startswith("/api/v1/demo/yolo-person/stream")
    assert payload["confidence_threshold"] == 0.4
    assert payload["iou_threshold"] == 0.6
    assert payload["inference_stride"] == 4
    assert "inference_stride=4" in payload["stream_url"]
    assert "no identifica" in payload["privacy_note"]


def test_yolo_restaurant_detection_status_endpoint_exposes_coco_demo_classes() -> None:
    client = make_client()

    response = client.get("/api/v1/demo/yolo-restaurant/status?confidence=0.3&inference_stride=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stream_url"].startswith("/api/v1/demo/yolo-restaurant/stream")
    assert payload["confidence_threshold"] == 0.3
    assert payload["inference_stride"] == 5
    assert "inference_stride=5" in payload["stream_url"]
    assert "person" in payload["allowed_labels"]
    assert "chair" in payload["allowed_labels"]
    assert "dining table" in payload["allowed_labels"]
    assert "ROI" in payload["usage_note"]


def test_table_service_analysis_endpoint_returns_waiting_state_before_stream() -> None:
    client = make_client()

    response = client.get("/api/v1/demo/table-service/analysis?table_id=table_01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_id"] == "table_01"
    assert payload["state"] == "waiting_for_video"
    assert payload["people_count"] == 0


def test_table_service_analysis_endpoint_exposes_latest_shared_stream_state() -> None:
    client = make_client()
    monitor = TableServiceMonitor(TableServiceMonitorConfig(table_id="table_42"))
    analysis = monitor.process(
        [
            ScoredDetection("person_1", BoundingBox(0, 0, 100, 200), 0.92, "person"),
            ScoredDetection("fork_1", BoundingBox(0, 0, 10, 20), 0.82, "fork"),
        ],
        observed_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )
    client.app.state.table_service_analyses["table_42"] = analysis

    response = client.get("/api/v1/demo/table-service/analysis?table_id=table_42")

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_id"] == "table_42"
    assert payload["people_count"] == 1
    assert payload["object_counts"]["person"] == 1
    assert payload["object_counts"]["fork"] == 1
    assert payload["missing_items"]["knife"] == 1
    event_types = [event["event_type"] for event in payload["timeline_events"]]
    assert "table_session_started" in event_types
    assert "missing_table_setup" in event_types


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
