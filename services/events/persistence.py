from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from services.events.models import (
    CameraStatus,
    DomainEvent,
    EventType,
    TableDefinition,
    TablePrediction,
    TableRuntime,
    TableSession,
    TableState,
    ZoneDefinition,
)


class Base(DeclarativeBase):
    pass


class CameraRow(Base):
    __tablename__ = "cameras"

    camera_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class ZoneRow(Base):
    __tablename__ = "zones"

    zone_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id"), nullable=False)
    polygon_definition: Mapped[list[list[int]]] = mapped_column(JSON, nullable=False)


class TableRow(Base):
    __tablename__ = "tables"

    table_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.zone_id"), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TableRuntimeRow(Base):
    __tablename__ = "table_runtime"

    table_id: Mapped[str] = mapped_column(ForeignKey("tables.table_id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    last_people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    people_count_peak: Mapped[int] = mapped_column(Integer, nullable=False)
    active_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.session_id"),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TableSessionRow(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    table_id: Mapped[str] = mapped_column(ForeignKey("tables.table_id"), nullable=False)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    people_count_initial: Mapped[int] = mapped_column(Integer, nullable=False)
    people_count_peak: Mapped[int] = mapped_column(Integer, nullable=False)
    final_status: Mapped[str | None] = mapped_column(String(60), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DomainEventRow(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id"), nullable=False)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.zone_id"), nullable=False)
    table_id: Mapped[str | None] = mapped_column(ForeignKey("tables.table_id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TablePredictionRow(Base):
    __tablename__ = "predictions"

    prediction_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    table_id: Mapped[str] = mapped_column(ForeignKey("tables.table_id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(String(500), nullable=False)


@dataclass(slots=True)
class PersistedMVPState:
    cameras: dict[str, CameraStatus]
    zones: dict[str, ZoneDefinition]
    tables: dict[str, TableDefinition]
    runtime_by_table: dict[str, TableRuntime]
    sessions_by_id: dict[str, TableSession]
    events: list[DomainEvent]
    predictions: list[TablePrediction]

    @property
    def has_topology(self) -> bool:
        return bool(self.cameras and self.zones and self.tables)


class SqlAlchemyMVPRepository:
    def __init__(self, database_url: str, echo: bool = False) -> None:
        self.engine = create_engine(database_url, echo=echo, future=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False, future=True)
        self.create_schema()

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def load_state(self) -> PersistedMVPState:
        with self.session_factory() as session:
            cameras = {
                row.camera_id: CameraStatus(
                    camera_id=row.camera_id,
                    name=row.name,
                    status=row.status,
                )
                for row in session.scalars(select(CameraRow).order_by(CameraRow.camera_id))
            }
            zones = {
                row.zone_id: ZoneDefinition(
                    zone_id=row.zone_id,
                    name=row.name,
                    camera_id=row.camera_id,
                    polygon_definition=row.polygon_definition,
                )
                for row in session.scalars(select(ZoneRow).order_by(ZoneRow.zone_id))
            }
            tables = {
                row.table_id: TableDefinition(
                    table_id=row.table_id,
                    name=row.name,
                    capacity=row.capacity,
                    zone_id=row.zone_id,
                    active=row.active,
                )
                for row in session.scalars(select(TableRow).order_by(TableRow.table_id))
            }
            runtime_by_table = {
                row.table_id: TableRuntime(
                    table_id=row.table_id,
                    state=TableState(row.state),
                    last_people_count=row.last_people_count,
                    people_count_peak=row.people_count_peak,
                    active_session_id=row.active_session_id,
                    updated_at=row.updated_at,
                )
                for row in session.scalars(
                    select(TableRuntimeRow).order_by(TableRuntimeRow.table_id)
                )
            }
            sessions_by_id = {
                row.session_id: self._session_from_row(row)
                for row in session.scalars(
                    select(TableSessionRow).order_by(TableSessionRow.start_ts)
                )
            }
            events = [
                self._event_from_row(row)
                for row in session.scalars(select(DomainEventRow).order_by(DomainEventRow.ts))
            ]
            predictions = [
                self._prediction_from_row(row)
                for row in session.scalars(
                    select(TablePredictionRow).order_by(TablePredictionRow.ts)
                )
            ]

        for table_id in tables:
            runtime_by_table.setdefault(table_id, TableRuntime(table_id=table_id))

        return PersistedMVPState(
            cameras=cameras,
            zones=zones,
            tables=tables,
            runtime_by_table=runtime_by_table,
            sessions_by_id=sessions_by_id,
            events=events,
            predictions=predictions,
        )

    def save_topology(
        self,
        cameras: dict[str, CameraStatus],
        zones: dict[str, ZoneDefinition],
        tables: dict[str, TableDefinition],
        runtime_by_table: dict[str, TableRuntime],
    ) -> None:
        with self.session_factory.begin() as session:
            for camera in cameras.values():
                session.merge(
                    CameraRow(
                        camera_id=camera.camera_id,
                        name=camera.name,
                        status=camera.status,
                    )
                )
            for zone in zones.values():
                session.merge(
                    ZoneRow(
                        zone_id=zone.zone_id,
                        name=zone.name,
                        camera_id=zone.camera_id,
                        polygon_definition=zone.polygon_definition,
                    )
                )
            for table in tables.values():
                session.merge(
                    TableRow(
                        table_id=table.table_id,
                        name=table.name,
                        capacity=table.capacity,
                        zone_id=table.zone_id,
                        active=table.active,
                    )
                )
            for runtime in runtime_by_table.values():
                session.merge(self._runtime_row(runtime))

    def save_runtime(self, runtime: TableRuntime) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._runtime_row(runtime))

    def save_session(self, table_session: TableSession) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._session_row(table_session))

    def save_events(self, events: list[DomainEvent]) -> None:
        if not events:
            return
        with self.session_factory.begin() as session:
            for event in events:
                session.merge(self._event_row(event))

    def save_prediction(self, prediction: TablePrediction) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._prediction_row(prediction))

    def _runtime_row(self, runtime: TableRuntime) -> TableRuntimeRow:
        return TableRuntimeRow(
            table_id=runtime.table_id,
            state=runtime.state.value,
            last_people_count=runtime.last_people_count,
            people_count_peak=runtime.people_count_peak,
            active_session_id=runtime.active_session_id,
            updated_at=runtime.updated_at,
        )

    def _session_row(self, table_session: TableSession) -> TableSessionRow:
        return TableSessionRow(
            session_id=table_session.session_id,
            table_id=table_session.table_id,
            start_ts=table_session.start_ts,
            end_ts=table_session.end_ts,
            people_count_initial=table_session.people_count_initial,
            people_count_peak=table_session.people_count_peak,
            final_status=table_session.final_status,
            duration_seconds=table_session.duration_seconds,
        )

    def _event_row(self, event: DomainEvent) -> DomainEventRow:
        return DomainEventRow(
            event_id=event.event_id,
            ts=event.ts,
            camera_id=event.camera_id,
            zone_id=event.zone_id,
            table_id=event.table_id,
            event_type=event.event_type.value,
            confidence=event.confidence,
            payload_json=event.payload_json,
        )

    def _prediction_row(self, prediction: TablePrediction) -> TablePredictionRow:
        return TablePredictionRow(
            prediction_id=prediction.prediction_id,
            ts=prediction.ts,
            table_id=prediction.table_id,
            model_name=prediction.model_name,
            prediction_type=prediction.prediction_type,
            value=prediction.value,
            lower_bound=prediction.lower_bound,
            upper_bound=prediction.upper_bound,
            confidence=prediction.confidence,
            explanation=prediction.explanation,
        )

    def _session_from_row(self, row: TableSessionRow) -> TableSession:
        return TableSession(
            session_id=row.session_id,
            table_id=row.table_id,
            start_ts=row.start_ts,
            end_ts=row.end_ts,
            people_count_initial=row.people_count_initial,
            people_count_peak=row.people_count_peak,
            final_status=row.final_status,
            duration_seconds=row.duration_seconds,
        )

    def _event_from_row(self, row: DomainEventRow) -> DomainEvent:
        return DomainEvent(
            event_id=row.event_id,
            ts=row.ts,
            camera_id=row.camera_id,
            zone_id=row.zone_id,
            table_id=row.table_id,
            event_type=EventType(row.event_type),
            confidence=row.confidence,
            payload_json=row.payload_json or {},
        )

    def _prediction_from_row(self, row: TablePredictionRow) -> TablePrediction:
        return TablePrediction(
            prediction_id=row.prediction_id,
            ts=row.ts,
            table_id=row.table_id,
            model_name=row.model_name,
            prediction_type=row.prediction_type,
            value=row.value,
            lower_bound=row.lower_bound,
            upper_bound=row.upper_bound,
            confidence=row.confidence,
            explanation=row.explanation,
        )
