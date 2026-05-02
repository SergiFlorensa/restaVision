from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from services.alerts.anomaly import OperationalAlert, OperationalAnomalyDetector
from services.decision_engine import NextBestActionEngine
from services.decision_engine.models import (
    DecisionFeedback,
    DecisionRecommendation,
    QueueGroupSnapshot,
    ServiceContext,
)
from services.decision_engine.models import TableSnapshot as DecisionTableSnapshot
from services.events.models import (
    CameraStatus,
    DomainEvent,
    EventType,
    ObservationResult,
    OperationalAction,
    TableDefinition,
    TableObservation,
    TableOperationalUpdate,
    TablePrediction,
    TableRuntime,
    TableSession,
    TableSnapshot,
    TableState,
    ZoneDefinition,
)
from services.events.occlusion import OcclusionManager, OcclusionStatus
from services.events.persistence import SqlAlchemyMVPRepository
from services.events.state_machine import TableStateMachine
from services.features.recorder import FeatureStoreRecorder
from services.prediction.eta import EtaBaselineService


class RestaurantMVPService:
    def __init__(
        self,
        state_machine: TableStateMachine | None = None,
        eta_service: EtaBaselineService | None = None,
        anomaly_detector: OperationalAnomalyDetector | None = None,
        repository: SqlAlchemyMVPRepository | None = None,
        feature_recorder: FeatureStoreRecorder | None = None,
        occlusion_manager: OcclusionManager | None = None,
    ) -> None:
        self.state_machine = state_machine or TableStateMachine()
        self.eta_service = eta_service or EtaBaselineService()
        self.anomaly_detector = anomaly_detector or OperationalAnomalyDetector()
        self.repository = repository
        self.feature_recorder = feature_recorder
        self.occlusion_manager = occlusion_manager
        self.cameras: dict[str, CameraStatus] = {}
        self.zones: dict[str, ZoneDefinition] = {}
        self.tables: dict[str, TableDefinition] = {}
        self.runtime_by_table: dict[str, TableRuntime] = {}
        self.sessions_by_id: dict[str, TableSession] = {}
        self.events: list[DomainEvent] = []
        self.predictions: list[TablePrediction] = []
        self.alerts: list[OperationalAlert] = []
        self.operational_actions: list[OperationalAction] = []
        self.queue_groups: dict[str, QueueGroupSnapshot] = {}
        self.decision_recommendations: dict[str, DecisionRecommendation] = {}
        self.decision_feedback: list[DecisionFeedback] = []
        self.next_best_action_engine = NextBestActionEngine()
        self._emitted_alert_keys: set[tuple[str, str, str]] = set()
        self._load_or_seed_state()

    def list_cameras(self) -> list[CameraStatus]:
        return list(self.cameras.values())

    def list_zones(self) -> list[ZoneDefinition]:
        return list(self.zones.values())

    def list_table_snapshots(self) -> list[TableSnapshot]:
        return [self.get_table_snapshot(table_id) for table_id in self.tables]

    def list_sessions(self) -> list[TableSession]:
        return sorted(self.sessions_by_id.values(), key=lambda item: item.start_ts, reverse=True)

    def list_events(self, limit: int = 50) -> list[DomainEvent]:
        return list(reversed(self.events[-limit:]))

    def list_predictions(self, limit: int = 50) -> list[TablePrediction]:
        return list(reversed(self.predictions[-limit:]))

    def list_alerts(self, limit: int = 50) -> list[OperationalAlert]:
        return list(reversed(self.alerts[-limit:]))

    def list_queue_groups(self) -> list[QueueGroupSnapshot]:
        return sorted(
            self.queue_groups.values(),
            key=lambda item: item.arrival_ts,
            reverse=True,
        )

    def create_queue_group(
        self,
        party_size: int,
        arrival_ts: datetime,
        preferred_zone_id: str | None = None,
    ) -> QueueGroupSnapshot:
        if preferred_zone_id is not None:
            self._get_zone(preferred_zone_id)
        queue_group = QueueGroupSnapshot(
            queue_group_id=self._new_id("queue_group"),
            party_size=party_size,
            arrival_ts=arrival_ts,
            preferred_zone_id=preferred_zone_id,
        )
        self.queue_groups[queue_group.queue_group_id] = queue_group
        if self.repository is not None:
            self.repository.save_queue_group(queue_group)
        return queue_group

    def recommend_next_best_action(self, limit: int = 3) -> list[DecisionRecommendation]:
        context = self._decision_context(datetime.now(UTC))
        recommendations = self.next_best_action_engine.recommend_top(context, limit=limit)
        for recommendation in recommendations:
            self.decision_recommendations[recommendation.decision_id] = recommendation
            if self.repository is not None:
                self.repository.save_decision_recommendation(recommendation, ts=context.now)
        return recommendations

    def record_decision_feedback(
        self,
        decision_id: str,
        feedback_type: str,
        accepted: bool,
        useful: bool | None = None,
        outcome: dict[str, object] | None = None,
        comment: str | None = None,
        ts: datetime | None = None,
    ) -> DecisionFeedback:
        if decision_id not in self.decision_recommendations:
            raise KeyError(f"Unknown decision_id: {decision_id}")
        feedback = DecisionFeedback(
            feedback_id=self._new_id("feedback"),
            decision_id=decision_id,
            ts=ts or datetime.now(UTC),
            feedback_type=feedback_type,
            accepted=accepted,
            useful=useful,
            outcome=outcome or {},
            comment=comment,
        )
        self.decision_feedback.append(feedback)
        if self.repository is not None:
            self.repository.save_decision_feedback(feedback)
        return feedback

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
            phase=runtime.phase,
            needs_attention=runtime.needs_attention,
            assigned_staff=runtime.assigned_staff,
            last_attention_at=runtime.last_attention_at,
            operational_note=runtime.operational_note,
        )

    def update_table_runtime(
        self,
        table_id: str,
        update: TableOperationalUpdate,
        ts: datetime | None = None,
    ) -> TableSnapshot:
        table = self._get_table(table_id)
        runtime = self.runtime_by_table[table_id]
        timestamp = ts or datetime.now(UTC)
        updated_runtime = replace(
            runtime,
            state=update.state or runtime.state,
            last_people_count=(
                update.people_count
                if update.people_count is not None
                else runtime.last_people_count
            ),
            people_count_peak=max(
                runtime.people_count_peak,
                (
                    update.people_count
                    if update.people_count is not None
                    else runtime.people_count_peak
                ),
            ),
            updated_at=timestamp,
            phase=update.phase if update.phase is not None else runtime.phase,
            needs_attention=(
                update.needs_attention
                if update.needs_attention is not None
                else runtime.needs_attention
            ),
            assigned_staff=(
                update.assigned_staff
                if update.assigned_staff is not None
                else runtime.assigned_staff
            ),
            last_attention_at=(
                update.last_attention_at
                if update.last_attention_at is not None
                else runtime.last_attention_at
            ),
            operational_note=(
                update.operational_note
                if update.operational_note is not None
                else runtime.operational_note
            ),
        )
        self.runtime_by_table[table_id] = updated_runtime
        event = DomainEvent(
            event_id=self._new_id("evt"),
            ts=timestamp,
            camera_id=self.zones[table.zone_id].camera_id,
            zone_id=table.zone_id,
            table_id=table.table_id,
            event_type=EventType.TABLE_STATE_CHANGED,
            confidence=1.0,
            payload_json={
                "source": "manual_operational_update",
                "state": updated_runtime.state.value,
                "phase": updated_runtime.phase,
                "needs_attention": updated_runtime.needs_attention,
                "assigned_staff": updated_runtime.assigned_staff,
                "operational_note": updated_runtime.operational_note,
            },
        )
        self.events.append(event)
        if self.repository is not None:
            self.repository.save_runtime(updated_runtime)
            self.repository.save_events([event])
        return self.get_table_snapshot(table_id)

    def record_operational_action(
        self,
        action_type: str,
        table_id: str | None = None,
        queue_group_id: str | None = None,
        assigned_staff: str | None = None,
        target_channel: str = "shared_panel",
        message: str | None = None,
        payload: dict[str, object] | None = None,
        ts: datetime | None = None,
    ) -> OperationalAction:
        timestamp = ts or datetime.now(UTC)
        if table_id is not None:
            self._get_table(table_id)
        if queue_group_id is not None and queue_group_id not in self.queue_groups:
            raise KeyError(f"Unknown queue_group_id: {queue_group_id}")

        action = OperationalAction(
            action_id=self._new_id("action"),
            ts=timestamp,
            action_type=action_type,
            table_id=table_id,
            queue_group_id=queue_group_id,
            assigned_staff=assigned_staff,
            target_channel=target_channel,
            message=message,
            payload_json=payload or {},
        )
        self.operational_actions.append(action)
        if self.repository is not None:
            self.repository.save_operational_action(action)
        if table_id is not None:
            self._apply_action_to_table(action)
        return action

    def _apply_action_to_table(self, action: OperationalAction) -> None:
        if action.table_id is None:
            return
        if action.action_type == "mark_needs_attention":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    needs_attention=True,
                    assigned_staff=action.assigned_staff,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )
        elif action.action_type == "attention_done":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    needs_attention=False,
                    last_attention_at=action.ts,
                    assigned_staff=action.assigned_staff,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )
        elif action.action_type == "request_bill":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    state=TableState.PAYMENT,
                    phase="bill_requested",
                    assigned_staff=action.assigned_staff,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )
        elif action.action_type == "start_cleaning":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    state=TableState.PENDING_CLEANING,
                    phase="cleaning",
                    assigned_staff=action.assigned_staff,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )
        elif action.action_type == "cleaning_done":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    state=TableState.READY,
                    phase="idle",
                    people_count=0,
                    needs_attention=False,
                    assigned_staff=action.assigned_staff,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )
        elif action.action_type == "seat_group":
            self.update_table_runtime(
                action.table_id,
                TableOperationalUpdate(
                    state=TableState.OCCUPIED,
                    phase="seated",
                    people_count=int(action.payload_json.get("party_size", 0) or 0),
                    assigned_staff=action.assigned_staff,
                    last_attention_at=action.ts,
                    operational_note=action.message,
                ),
                ts=action.ts,
            )

    def process_observation(self, observation: TableObservation) -> ObservationResult:
        table = self._get_table(observation.table_id)
        self._get_zone(observation.zone_id)
        runtime = self.runtime_by_table[observation.table_id]
        active_session = self._get_active_session(runtime)
        effective_observation = observation
        occlusion_decision = None
        if self.occlusion_manager is not None:
            occlusion_decision = self.occlusion_manager.apply(
                runtime=runtime,
                observation=observation,
            )
            effective_observation = occlusion_decision.effective_observation

        transition = self.state_machine.apply(
            table=table,
            zone=self.zones[observation.zone_id],
            runtime=runtime,
            observation=effective_observation,
            active_session=active_session,
        )
        if occlusion_decision is not None and occlusion_decision.held_previous_count:
            transition.events.append(
                self._occlusion_event(
                    event_type=(
                        EventType.CAMERA_BLOCKED
                        if occlusion_decision.status is OcclusionStatus.CAMERA_BLOCKED
                        else EventType.OCCLUSION_SUSPECTED
                    ),
                    observation=observation,
                    payload={
                        "status": occlusion_decision.status.value,
                        "reason": occlusion_decision.reason,
                        "raw_people_count": observation.people_count,
                        "held_people_count": effective_observation.people_count,
                        "raw_confidence": observation.confidence,
                        "effective_confidence": effective_observation.confidence,
                        "empty_observation_count": occlusion_decision.empty_observation_count,
                        "blocked_observation_count": occlusion_decision.blocked_observation_count,
                    },
                )
            )
        self.runtime_by_table[table.table_id] = transition.runtime

        if transition.session_upsert is not None:
            self.sessions_by_id[transition.session_upsert.session_id] = transition.session_upsert
            if self.repository is not None:
                self.repository.save_session(transition.session_upsert)

        self.events.extend(transition.events)
        if self.repository is not None:
            self.repository.save_runtime(transition.runtime)
            self.repository.save_events(transition.events)

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
            if self.repository is not None:
                self.repository.save_prediction(prediction)

            alert = self.anomaly_detector.detect_long_session(
                table_id=table.table_id,
                active_session=current_session,
                historical_sessions=historical_sessions,
                now=observation.observed_at,
            )
            if alert is not None:
                self._append_alert_once(alert)

        result = ObservationResult(
            table=self.get_table_snapshot(table.table_id),
            session=current_session,
            events=transition.events,
            prediction=prediction,
        )
        if self.feature_recorder is not None:
            self.feature_recorder.record_observation_result(observation, result)
        return result

    def mark_table_ready(self, table_id: str, observed_at: datetime | None = None) -> TableSnapshot:
        table = self._get_table(table_id)
        runtime = self.runtime_by_table[table_id]
        if runtime.state != TableState.PENDING_CLEANING:
            raise ValueError("The table is not waiting for cleaning confirmation.")

        timestamp = observed_at or datetime.now(UTC)
        previous_state = runtime.state
        updated_runtime = replace(
            runtime,
            state=TableState.READY,
            last_people_count=0,
            people_count_peak=0,
            updated_at=timestamp,
        )
        self.runtime_by_table[table_id] = updated_runtime
        events = [
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
        self.events.extend(events)
        if self.repository is not None:
            self.repository.save_runtime(updated_runtime)
            self.repository.save_events(events)
        snapshot = self.get_table_snapshot(table_id)
        if self.feature_recorder is not None:
            self.feature_recorder.record_manual_state_change(
                table_id=table.table_id,
                current_state=snapshot.state.value,
                observed_at=timestamp,
                confidence=1.0,
                people_count=snapshot.people_count,
                events=events,
            )
        return snapshot

    def upsert_camera(self, camera: CameraStatus) -> CameraStatus:
        self.cameras[camera.camera_id] = camera
        self._persist_topology()
        return camera

    def upsert_zone(self, zone: ZoneDefinition) -> ZoneDefinition:
        if zone.camera_id not in self.cameras:
            raise KeyError(f"Unknown camera_id: {zone.camera_id}")

        self.zones[zone.zone_id] = zone
        self._persist_topology()
        return zone

    def upsert_table(self, table: TableDefinition) -> TableSnapshot:
        self._get_zone(table.zone_id)
        self.tables[table.table_id] = table
        self.runtime_by_table.setdefault(table.table_id, TableRuntime(table_id=table.table_id))
        self._persist_topology()
        return self.get_table_snapshot(table.table_id)

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
        table = TableDefinition(
            table_id="table_01", name="Mesa 01", capacity=4, zone_id=zone.zone_id
        )
        self.cameras[camera.camera_id] = camera
        self.zones[zone.zone_id] = zone
        self.tables[table.table_id] = table
        self.runtime_by_table[table.table_id] = TableRuntime(table_id=table.table_id)

    def _load_or_seed_state(self) -> None:
        if self.repository is None:
            self._seed_demo_topology()
            return

        persisted_state = self.repository.load_state()
        if not persisted_state.has_topology:
            self._seed_demo_topology()
            self.repository.save_topology(
                cameras=self.cameras,
                zones=self.zones,
                tables=self.tables,
                runtime_by_table=self.runtime_by_table,
            )
            return

        self.cameras = persisted_state.cameras
        self.zones = persisted_state.zones
        self.tables = persisted_state.tables
        self.runtime_by_table = persisted_state.runtime_by_table
        self.sessions_by_id = persisted_state.sessions_by_id
        self.events = persisted_state.events
        self.predictions = persisted_state.predictions
        self.queue_groups = persisted_state.queue_groups
        self.decision_recommendations = persisted_state.decision_recommendations
        self.decision_feedback = persisted_state.decision_feedback
        self.operational_actions = persisted_state.operational_actions

    def _persist_topology(self) -> None:
        if self.repository is None:
            return
        self.repository.save_topology(
            cameras=self.cameras,
            zones=self.zones,
            tables=self.tables,
            runtime_by_table=self.runtime_by_table,
        )

    def _append_alert_once(self, alert: OperationalAlert) -> None:
        key = (
            alert.table_id,
            alert.session_id or "without_session",
            alert.alert_type.value,
        )
        if key in self._emitted_alert_keys:
            return
        self._emitted_alert_keys.add(key)
        self.alerts.append(alert)

    def _decision_context(self, now: datetime) -> ServiceContext:
        return ServiceContext(
            now=now,
            tables=tuple(self._decision_table_snapshot(table_id, now) for table_id in self.tables),
            queue_groups=tuple(self.queue_groups.values()),
            p1_alert_count=len(self.alerts),
        )

    def _decision_table_snapshot(self, table_id: str, now: datetime) -> DecisionTableSnapshot:
        table = self._get_table(table_id)
        runtime = self.runtime_by_table[table_id]
        active_session_minutes = 0.0
        if runtime.active_session_id is not None:
            session = self.sessions_by_id.get(runtime.active_session_id)
            if session is not None:
                active_session_minutes = max(
                    0.0,
                    (now - session.start_ts).total_seconds() / 60,
                )
        return DecisionTableSnapshot(
            table_id=table.table_id,
            capacity=table.capacity,
            state=runtime.state.value,
            active_session_minutes=active_session_minutes,
            eta_minutes=self._latest_eta_minutes(table.table_id),
            zone_id=table.zone_id,
            needs_attention=runtime.needs_attention,
        )

    def _latest_eta_minutes(self, table_id: str) -> float | None:
        for prediction in reversed(self.predictions):
            if prediction.table_id == table_id and prediction.prediction_type == "eta_seconds":
                return prediction.value / 60
        return None

    def _occlusion_event(
        self,
        event_type: EventType,
        observation: TableObservation,
        payload: dict[str, object],
    ) -> DomainEvent:
        return DomainEvent(
            event_id=self._new_id("evt"),
            ts=observation.observed_at,
            camera_id=observation.camera_id,
            zone_id=observation.zone_id,
            table_id=observation.table_id,
            event_type=event_type,
            confidence=observation.confidence,
            payload_json=payload,
        )

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"
