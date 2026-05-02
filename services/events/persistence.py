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
    inspect,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from services.decision_engine.models import (
    DecisionFeedback,
    DecisionRecommendation,
    QueueGroupSnapshot,
)
from services.events.models import (
    CameraStatus,
    DomainEvent,
    EventType,
    OperationalAction,
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
    phase: Mapped[str] = mapped_column(String(60), nullable=False, default="idle")
    needs_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assigned_staff: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_attention_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    operational_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


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


class QueueGroupRow(Base):
    __tablename__ = "queue_groups"

    queue_group_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    arrival_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    promised_wait_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promised_wait_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    promised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preferred_zone_id: Mapped[str | None] = mapped_column(String(80), nullable=True)


class DecisionRecommendationRow(Base):
    __tablename__ = "decision_recommendations"

    decision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    question: Mapped[str] = mapped_column(String(200), nullable=False)
    answer: Mapped[str] = mapped_column(String(300), nullable=False)
    table_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    queue_group_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eta_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    impact: Mapped[str] = mapped_column(String(80), nullable=False)
    reason_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expires_in_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DecisionFeedbackRow(Base):
    __tablename__ = "decision_feedback"

    feedback_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decision_recommendations.decision_id"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(60), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    useful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    outcome_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)


class OperationalActionRow(Base):
    __tablename__ = "operational_actions"

    action_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    table_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    queue_group_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    assigned_staff: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_channel: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


@dataclass(slots=True)
class PersistedMVPState:
    cameras: dict[str, CameraStatus]
    zones: dict[str, ZoneDefinition]
    tables: dict[str, TableDefinition]
    runtime_by_table: dict[str, TableRuntime]
    sessions_by_id: dict[str, TableSession]
    events: list[DomainEvent]
    predictions: list[TablePrediction]
    queue_groups: dict[str, QueueGroupSnapshot]
    decision_recommendations: dict[str, DecisionRecommendation]
    decision_feedback: list[DecisionFeedback]
    operational_actions: list[OperationalAction]

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
        self._ensure_runtime_columns()

    def _ensure_runtime_columns(self) -> None:
        inspector = inspect(self.engine)
        if not inspector.has_table("table_runtime"):
            return
        existing = {column["name"] for column in inspector.get_columns("table_runtime")}
        statements = {
            "phase": (
                "ALTER TABLE table_runtime ADD COLUMN phase VARCHAR(60) NOT NULL DEFAULT 'idle'"
            ),
            "needs_attention": (
                "ALTER TABLE table_runtime "
                "ADD COLUMN needs_attention BOOLEAN NOT NULL DEFAULT false"
            ),
            "assigned_staff": ("ALTER TABLE table_runtime ADD COLUMN assigned_staff VARCHAR(120)"),
            "last_attention_at": (
                "ALTER TABLE table_runtime ADD COLUMN last_attention_at TIMESTAMP"
            ),
            "operational_note": (
                "ALTER TABLE table_runtime ADD COLUMN operational_note VARCHAR(500)"
            ),
        }
        with self.engine.begin() as connection:
            for column_name, statement in statements.items():
                if column_name not in existing:
                    connection.execute(text(statement))

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
                    phase=row.phase,
                    needs_attention=row.needs_attention,
                    assigned_staff=row.assigned_staff,
                    last_attention_at=row.last_attention_at,
                    operational_note=row.operational_note,
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
            queue_groups = {
                row.queue_group_id: self._queue_group_from_row(row)
                for row in session.scalars(select(QueueGroupRow).order_by(QueueGroupRow.arrival_ts))
            }
            decision_recommendations = {
                row.decision_id: self._decision_from_row(row)
                for row in session.scalars(
                    select(DecisionRecommendationRow).order_by(DecisionRecommendationRow.ts)
                )
            }
            decision_feedback = [
                self._feedback_from_row(row)
                for row in session.scalars(
                    select(DecisionFeedbackRow).order_by(DecisionFeedbackRow.ts)
                )
            ]
            operational_actions = [
                self._operational_action_from_row(row)
                for row in session.scalars(
                    select(OperationalActionRow).order_by(OperationalActionRow.ts)
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
            queue_groups=queue_groups,
            decision_recommendations=decision_recommendations,
            decision_feedback=decision_feedback,
            operational_actions=operational_actions,
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

    def save_queue_group(self, queue_group: QueueGroupSnapshot) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._queue_group_row(queue_group))

    def save_decision_recommendation(self, decision: DecisionRecommendation, ts: datetime) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._decision_row(decision, ts))

    def save_decision_feedback(self, feedback: DecisionFeedback) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._feedback_row(feedback))

    def save_operational_action(self, action: OperationalAction) -> None:
        with self.session_factory.begin() as session:
            session.merge(self._operational_action_row(action))

    def _runtime_row(self, runtime: TableRuntime) -> TableRuntimeRow:
        return TableRuntimeRow(
            table_id=runtime.table_id,
            state=runtime.state.value,
            last_people_count=runtime.last_people_count,
            people_count_peak=runtime.people_count_peak,
            active_session_id=runtime.active_session_id,
            updated_at=runtime.updated_at,
            phase=runtime.phase,
            needs_attention=runtime.needs_attention,
            assigned_staff=runtime.assigned_staff,
            last_attention_at=runtime.last_attention_at,
            operational_note=runtime.operational_note,
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

    def _queue_group_row(self, queue_group: QueueGroupSnapshot) -> QueueGroupRow:
        return QueueGroupRow(
            queue_group_id=queue_group.queue_group_id,
            arrival_ts=queue_group.arrival_ts,
            party_size=queue_group.party_size,
            status=str(queue_group.status),
            promised_wait_min=queue_group.promised_wait_min,
            promised_wait_max=queue_group.promised_wait_max,
            promised_at=queue_group.promised_at,
            preferred_zone_id=queue_group.preferred_zone_id,
        )

    def _decision_row(
        self,
        decision: DecisionRecommendation,
        ts: datetime,
    ) -> DecisionRecommendationRow:
        return DecisionRecommendationRow(
            decision_id=decision.decision_id,
            ts=ts,
            mode=decision.mode,
            priority=decision.priority,
            question=decision.question,
            answer=decision.answer,
            table_id=decision.table_id,
            queue_group_id=decision.queue_group_id,
            eta_minutes=decision.eta_minutes,
            confidence=decision.confidence,
            impact=decision.impact,
            reason_json=list(decision.reason),
            expires_in_seconds=decision.expires_in_seconds,
            metadata_json=decision.metadata,
        )

    def _feedback_row(self, feedback: DecisionFeedback) -> DecisionFeedbackRow:
        return DecisionFeedbackRow(
            feedback_id=feedback.feedback_id,
            decision_id=feedback.decision_id,
            ts=feedback.ts,
            feedback_type=feedback.feedback_type,
            accepted=feedback.accepted,
            useful=feedback.useful,
            outcome_json=feedback.outcome,
            comment=feedback.comment,
        )

    def _operational_action_row(self, action: OperationalAction) -> OperationalActionRow:
        return OperationalActionRow(
            action_id=action.action_id,
            ts=action.ts,
            action_type=action.action_type,
            table_id=action.table_id,
            queue_group_id=action.queue_group_id,
            assigned_staff=action.assigned_staff,
            target_channel=action.target_channel,
            message=action.message,
            payload_json=action.payload_json,
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

    def _queue_group_from_row(self, row: QueueGroupRow) -> QueueGroupSnapshot:
        return QueueGroupSnapshot(
            queue_group_id=row.queue_group_id,
            arrival_ts=row.arrival_ts,
            party_size=row.party_size,
            status=row.status,
            promised_wait_min=row.promised_wait_min,
            promised_wait_max=row.promised_wait_max,
            promised_at=row.promised_at,
            preferred_zone_id=row.preferred_zone_id,
        )

    def _decision_from_row(self, row: DecisionRecommendationRow) -> DecisionRecommendation:
        return DecisionRecommendation(
            decision_id=row.decision_id,
            mode=row.mode,
            priority=row.priority,
            question=row.question,
            answer=row.answer,
            table_id=row.table_id,
            queue_group_id=row.queue_group_id,
            eta_minutes=row.eta_minutes,
            confidence=row.confidence,
            impact=row.impact,
            reason=tuple(row.reason_json or ()),
            expires_in_seconds=row.expires_in_seconds,
            metadata=row.metadata_json or {},
        )

    def _feedback_from_row(self, row: DecisionFeedbackRow) -> DecisionFeedback:
        return DecisionFeedback(
            feedback_id=row.feedback_id,
            decision_id=row.decision_id,
            ts=row.ts,
            feedback_type=row.feedback_type,
            accepted=row.accepted,
            useful=row.useful,
            outcome=row.outcome_json or {},
            comment=row.comment,
        )

    def _operational_action_from_row(self, row: OperationalActionRow) -> OperationalAction:
        return OperationalAction(
            action_id=row.action_id,
            ts=row.ts,
            action_type=row.action_type,
            table_id=row.table_id,
            queue_group_id=row.queue_group_id,
            assigned_staff=row.assigned_staff,
            target_channel=row.target_channel,
            message=row.message,
            payload_json=row.payload_json or {},
        )
