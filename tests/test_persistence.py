from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.events.models import (
    CameraStatus,
    TableDefinition,
    TableObservation,
    TableState,
    ZoneDefinition,
)
from services.events.persistence import SqlAlchemyMVPRepository
from services.events.service import RestaurantMVPService


def test_sqlalchemy_repository_persists_mvp_state_across_service_instances() -> None:
    repository = SqlAlchemyMVPRepository("sqlite+pysqlite:///:memory:")
    service = RestaurantMVPService(repository=repository)
    start = datetime(2026, 4, 13, 12, 0, tzinfo=UTC)

    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=3,
            confidence=0.98,
            observed_at=start,
        )
    )
    service.process_observation(
        TableObservation(
            camera_id="camera_mvp_01",
            zone_id="zone_table_01",
            table_id="table_01",
            people_count=0,
            confidence=0.98,
            observed_at=start + timedelta(minutes=45),
        )
    )

    reloaded = RestaurantMVPService(repository=repository)

    snapshot = reloaded.get_table_snapshot("table_01")
    assert snapshot.state is TableState.PENDING_CLEANING
    assert snapshot.people_count == 0

    sessions = reloaded.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].duration_seconds == 2700
    assert sessions[0].people_count_peak == 3

    assert len(reloaded.list_events(limit=100)) >= 7
    assert len(reloaded.list_predictions(limit=100)) == 1


def test_sqlalchemy_repository_persists_editable_topology() -> None:
    repository = SqlAlchemyMVPRepository("sqlite+pysqlite:///:memory:")
    service = RestaurantMVPService(repository=repository)

    service.upsert_camera(CameraStatus(camera_id="camera_02", name="Camara 02"))
    service.upsert_zone(
        ZoneDefinition(
            zone_id="zone_table_02",
            name="Zona Mesa 02",
            camera_id="camera_02",
            polygon_definition=[[10, 10], [300, 10], [300, 220], [10, 220]],
        )
    )
    service.upsert_table(
        TableDefinition(
            table_id="table_02",
            name="Mesa 02",
            capacity=6,
            zone_id="zone_table_02",
        )
    )

    reloaded = RestaurantMVPService(repository=repository)

    assert {camera.camera_id for camera in reloaded.list_cameras()} >= {
        "camera_mvp_01",
        "camera_02",
    }
    assert {zone.zone_id for zone in reloaded.list_zones()} >= {
        "zone_table_01",
        "zone_table_02",
    }

    table_ids = {table.table_id for table in reloaded.list_table_snapshots()}
    assert table_ids >= {"table_01", "table_02"}
