from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from services.events.models import (
    CameraStatus,
    DomainEvent,
    EventType,
    ObservationResult,
    TableDefinition,
    TableObservation,
    TablePrediction,
    TableRuntime,
    TableSession,
    TableSnapshot,
    TableState,
    ZoneDefinition,
)
from services.events.state_machine import TableStateMachine
from services.prediction.eta import EtaBaselineService


class RestaurantMVPService:
    def __init__(
        self,
        state_machine: TableStateMachine | None = None,
        eta_service: EtaBaselineService | None = None,
    ) -> None:
        self.state_machine = state_machine or TableStateMachine()
        self.eta_service = eta_service or EtaBaselineService()
        self.cameras: dict[str, CameraStatus] = {}
        self.zones: dict[str, ZoneDefinition] = {}
        self.tables: dict[str, TableDefinition] = {}
        self.runtime_by_table: dict[str, TableRuntime] = {}
        self.sessions_by_id: dict[str, TableSession] = {}
        self.events: list[DomainEvent] = []
        self.predictions: list[TablePrediction] = []
        self._seed_demo_topology()

    def list_cameras(self) -> list[CameraStatus]:
        return list(self.cameras.values())

    def list_table_snapshots(self) -> list[TableSnapshot]:
        return [self.get_table_snapshot(table_id) for table_id in self.tables]

    def list_sessions(self) -> list[TableSession]:
        return sorted(self.sessions_by_id.values(), key=lambda item: item.start_ts, reverse=True)

    def list_events(self, limit: int = 50) -> list[DomainEvent]:
        return list(reversed(self.events[-limit:]))

    def list_predictions(self, limit: int = 50) -> list[TablePrediction]:
        return list(reversed(self.predictions[-limit:]))

    def get_table_snapshot(self, table_id: str) -> TableSnapshot:
        table = self._get_table(table_id)
        runtime = self.runtime_by_table[table_id]
        return TableSnapshot(
            table_id=table.table_id,
            name=table.name,
            capacity=table.capacity,
            zone_id=table.zone_id,
            state=runtime.state,
            people_count=runtime.last_people_count,
            people_count_peak=runtime.people_count_peak,
            active_session_id=runtime.active_session_id,
            updated_at=runtime.updated_at,
        )

    def process_observation(self, observation: TableObservation) -> ObservationResult:
        table = self._get_table(observation.table_id)
        self._get_zone(observation.zone_id)
        runtime = self.runtime_by_table[observation.table_id]
        active_session = self._get_active_session(runtime)
        transition = self.state_machine.apply(
            table=table,
            zone=self.zones[observation.zone_id],
            runtime=runtime,
            observation=observation,
            active_session=active_session,
        )
        self.runtime_by_table[table.table_id] = transition.runtime

        if transition.session_upsert is not None:
            self.sessions_by_id[transition.session_upsert.session_id] = transition.session_upsert

        self.events.extend(transition.events)

        current_session = self._get_active_session(transition.runtime)
        prediction = None
        if current_session is not None:
            historical_sessions = [
                session
                for session in self.sessions_by_id.values()
                if session.table_id == table.table_id and session.end_ts is not None
            ]
            prediction = self.eta_service.predict(
                table_id=table.table_id,
                active_session=current_session,
                historical_sessions=historical_sessions,
                now=observation.observed_at,
            )
            self.predictions.append(prediction)

        return ObservationResult(
            table=self.get_table_snapshot(table.table_id),
            session=current_session,
            events=transition.events,
            prediction=prediction,
        )

    def mark_table_ready(self, table_id: str, observed_at: datetime | None = None) -> TableSnapshot:
        table = self._get_table(table_id)
        runtime = self.runtime_by_table[table_id]
        if runtime.state != TableState.PENDING_CLEANING:
            raise ValueError("The table is not waiting for cleaning confirmation.")

        timestamp = observed_at or datetime.now(timezone.utc)
        previous_state = runtime.state
        updated_runtime = replace(
            runtime,
            state=TableState.READY,
            last_people_count=0,
            people_count_peak=0,
            updated_at=timestamp,
        )
        self.runtime_by_table[table_id] = updated_runtime
        self.events.extend(
            [
                DomainEvent(
                    event_id=self._new_id("evt"),
                    ts=timestamp,
                    camera_id=self.zones[table.zone_id].camera_id,
                    zone_id=table.zone_id,
                    table_id=table.table_id,
                    event_type=EventType.TABLE_READY,
                    confidence=1.0,
                    payload_json={"table_id": table.table_id},
                ),
                DomainEvent(
                    event_id=self._new_id("evt"),
                    ts=timestamp,
                    camera_id=self.zones[table.zone_id].camera_id,
                    zone_id=table.zone_id,
                    table_id=table.table_id,
                    event_type=EventType.TABLE_STATE_CHANGED,
                    confidence=1.0,
                    payload_json={
                        "from_state": previous_state.value,
                        "to_state": TableState.READY.value,
                    },
                ),
            ]
        )
        return self.get_table_snapshot(table_id)

    def _get_table(self, table_id: str) -> TableDefinition:
        try:
            return self.tables[table_id]
        except KeyError as exc:
            raise KeyError(f"Unknown table_id: {table_id}") from exc

    def _get_zone(self, zone_id: str) -> ZoneDefinition:
        try:
            return self.zones[zone_id]
        except KeyError as exc:
            raise KeyError(f"Unknown zone_id: {zone_id}") from exc

    def _get_active_session(self, runtime: TableRuntime) -> TableSession | None:
        if runtime.active_session_id is None:
            return None
        return self.sessions_by_id.get(runtime.active_session_id)

    def _seed_demo_topology(self) -> None:
        camera = CameraStatus(camera_id="camera_mvp_01", name="Camara MVP 01")
        zone = ZoneDefinition(
            zone_id="zone_table_01",
            name="Zona Mesa 01",
            camera_id=camera.camera_id,
            polygon_definition=[[0, 0], [640, 0], [640, 480], [0, 480]],
        )
        table = TableDefinition(table_id="table_01", name="Mesa 01", capacity=4, zone_id=zone.zone_id)
        self.cameras[camera.camera_id] = camera
        self.zones[zone.zone_id] = zone
        self.tables[table.table_id] = table
        self.runtime_by_table[table.table_id] = TableRuntime(table_id=table.table_id)

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

