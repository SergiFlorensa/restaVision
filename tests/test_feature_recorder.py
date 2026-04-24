from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.events.models import TableObservation, TableState
from services.events.service import RestaurantMVPService
from services.features.recorder import FeatureStoreRecorder, FeatureStoreRecorderConfig
from services.features.store import ModelMetadata, SQLiteFeatureStore


def test_restaurant_service_records_feature_store_snapshot_and_lineage(tmp_path) -> None:
    store = SQLiteFeatureStore(tmp_path / "features.db")
    recorder = _make_recorder(store)
    service = RestaurantMVPService(feature_recorder=recorder)
    observed_at = datetime(2026, 4, 24, 13, 0, tzinfo=UTC)

    result = service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=2,
            confidence=0.96,
            observed_at=observed_at,
        )
    )

    snapshot = store.get_table_feature("table_01")
    lineage_events = store.list_lineage_events(limit=20)

    assert result.table.state is TableState.OCCUPIED
    assert snapshot is not None
    assert snapshot.current_state == TableState.OCCUPIED.value
    assert snapshot.confidence_score == 0.96
    assert snapshot.people_count == 2
    assert len(lineage_events) == len(result.events)
    assert {event.model_version for event in lineage_events} == {"yolo11n_int8_v1"}


def test_mark_table_ready_updates_feature_store_current_state(tmp_path) -> None:
    store = SQLiteFeatureStore(tmp_path / "features.db")
    recorder = _make_recorder(store)
    service = RestaurantMVPService(feature_recorder=recorder)
    start = datetime(2026, 4, 24, 13, 0, tzinfo=UTC)
    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=2,
            confidence=0.96,
            observed_at=start,
        )
    )
    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=0,
            confidence=0.97,
            observed_at=start + timedelta(minutes=40),
        )
    )

    service.mark_table_ready("table_01", observed_at=start + timedelta(minutes=42))

    snapshot = store.get_table_feature("table_01")
    assert snapshot is not None
    assert snapshot.current_state == TableState.READY.value
    assert snapshot.people_count == 0


def _make_recorder(store: SQLiteFeatureStore) -> FeatureStoreRecorder:
    model_metadata = ModelMetadata(
        model_version="yolo11n_int8_v1",
        model_path="models/exported/yolo11n_int8.xml",
        model_hash="abc123",
        input_width=640,
        input_height=640,
        runtime="openvino",
        quantization="int8",
        registered_at=datetime(2026, 4, 24, 12, 0, tzinfo=UTC),
    )
    return FeatureStoreRecorder(
        store=store,
        config=FeatureStoreRecorderConfig(model_version="yolo11n_int8_v1"),
        model_metadata=model_metadata,
    )
