from __future__ import annotations

from datetime import UTC, datetime

from services.features.store import (
    AILineageEvent,
    ModelMetadata,
    SQLiteFeatureStore,
    TableFeatureSnapshot,
)


def test_feature_store_registers_model_and_table_snapshot(tmp_path) -> None:
    store = SQLiteFeatureStore(tmp_path / "features.db")
    timestamp = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)

    store.register_model(
        ModelMetadata(
            model_version="yolo11n_int8_v1",
            model_path="models/exported/yolo11n_int8.xml",
            model_hash="abc123",
            input_width=640,
            input_height=640,
            runtime="openvino",
            quantization="int8",
            normalization={"scale": 1 / 255},
            registered_at=timestamp,
        )
    )
    store.upsert_table_feature(
        TableFeatureSnapshot(
            table_id="table_01",
            current_state="occupied",
            last_event_timestamp=timestamp,
            occupancy_duration_seconds=300,
            confidence_score=0.82,
            people_count=2,
            model_version="yolo11n_int8_v1",
            updated_at=timestamp,
        )
    )

    model = store.get_model("yolo11n_int8_v1")
    snapshot = store.get_table_feature("table_01")

    assert model is not None
    assert model.quantization == "int8"
    assert model.normalization == {"scale": 1 / 255}
    assert snapshot is not None
    assert snapshot.current_state == "occupied"
    assert snapshot.people_count == 2


def test_feature_store_lineage_event_is_idempotent(tmp_path) -> None:
    store = SQLiteFeatureStore(tmp_path / "features.db")
    timestamp = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    store.register_model(
        ModelMetadata(
            model_version="yolo11n_int8_v1",
            model_path="models/exported/yolo11n_int8.xml",
            model_hash="abc123",
            input_width=640,
            input_height=640,
            runtime="openvino",
            quantization="int8",
            registered_at=timestamp,
        )
    )
    event = AILineageEvent(
        event_id="evt_01",
        timestamp=timestamp,
        camera_id="camera_01",
        zone_id="zone_01",
        table_id="table_01",
        event_type="table_occupied",
        model_version="yolo11n_int8_v1",
        confidence_score=0.91,
        image_path="storage/anomalies/frame_01.jpg",
        latency_ms=18.5,
        payload_json={"people_count": 2},
        idempotency_key="camera_01:42:table_01:occupied",
    )

    inserted_first = store.append_lineage_event(event)
    inserted_second = store.append_lineage_event(event)
    events = store.list_lineage_events()

    assert inserted_first
    assert not inserted_second
    assert len(events) == 1
    assert events[0].payload_json == {"people_count": 2}
