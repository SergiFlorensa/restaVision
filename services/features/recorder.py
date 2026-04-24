from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.events.models import DomainEvent, ObservationResult, TableObservation, TableSession
from services.features.store import (
    AILineageEvent,
    ModelMetadata,
    SQLiteFeatureStore,
    TableFeatureSnapshot,
)


@dataclass(frozen=True, slots=True)
class FeatureStoreRecorderConfig:
    model_version: str
    image_path_payload_keys: tuple[str, ...] = ("image_path", "debug_artifact_ref")
    latency_ms_payload_keys: tuple[str, ...] = ("latency_ms", "inference_latency_ms")


class FeatureStoreRecorder:
    def __init__(
        self,
        store: SQLiteFeatureStore,
        config: FeatureStoreRecorderConfig,
        model_metadata: ModelMetadata | None = None,
    ) -> None:
        if model_metadata is not None and model_metadata.model_version != config.model_version:
            raise ValueError("model_metadata.model_version must match config.model_version.")
        self.store = store
        self.config = config
        if model_metadata is not None:
            self.store.register_model(model_metadata)

    def record_observation_result(
        self,
        observation: TableObservation,
        result: ObservationResult,
    ) -> None:
        self.record_table_feature(
            table_id=result.table.table_id,
            current_state=result.table.state.value,
            observed_at=observation.observed_at,
            confidence=observation.confidence,
            people_count=result.table.people_count,
            session=result.session,
        )
        self.record_events(result.events)

    def record_manual_state_change(
        self,
        table_id: str,
        current_state: str,
        observed_at: datetime,
        confidence: float,
        people_count: int,
        events: list[DomainEvent],
    ) -> None:
        self.record_table_feature(
            table_id=table_id,
            current_state=current_state,
            observed_at=observed_at,
            confidence=confidence,
            people_count=people_count,
            session=None,
        )
        self.record_events(events)

    def record_table_feature(
        self,
        table_id: str,
        current_state: str,
        observed_at: datetime,
        confidence: float,
        people_count: int,
        session: TableSession | None,
    ) -> None:
        occupancy_duration_seconds = 0.0
        if session is not None:
            occupancy_duration_seconds = max(
                0.0,
                (observed_at - session.start_ts).total_seconds(),
            )

        self.store.upsert_table_feature(
            TableFeatureSnapshot(
                table_id=table_id,
                current_state=current_state,
                last_event_timestamp=observed_at,
                occupancy_duration_seconds=occupancy_duration_seconds,
                confidence_score=confidence,
                people_count=people_count,
                model_version=self.config.model_version,
                updated_at=observed_at,
            )
        )

    def record_events(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.store.append_lineage_event(self._lineage_from_event(event))

    def _lineage_from_event(self, event: DomainEvent) -> AILineageEvent:
        payload = event.payload_json or {}
        return AILineageEvent(
            event_id=event.event_id,
            timestamp=event.ts,
            camera_id=event.camera_id,
            zone_id=event.zone_id,
            table_id=event.table_id,
            event_type=event.event_type.value,
            model_version=self.config.model_version,
            confidence_score=event.confidence,
            image_path=_first_payload_string(payload, self.config.image_path_payload_keys),
            latency_ms=_first_payload_float(payload, self.config.latency_ms_payload_keys),
            payload_json=payload,
            idempotency_key=_idempotency_key(event, payload),
        )


def _idempotency_key(event: DomainEvent, payload: dict[str, Any]) -> str:
    explicit_key = payload.get("idempotency_key")
    if isinstance(explicit_key, str) and explicit_key:
        return explicit_key
    return ":".join(
        [
            event.camera_id,
            event.zone_id,
            event.table_id or "no_table",
            event.event_type.value,
            event.ts.isoformat(),
        ]
    )


def _first_payload_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _first_payload_float(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int | float):
            return float(value)
    return None
