from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class TableState(StrEnum):
    READY = "ready"
    OCCUPIED = "occupied"
    FINALIZING = "finalizing"
    PAYMENT = "payment"
    PENDING_CLEANING = "pending_cleaning"


class EventType(StrEnum):
    PEOPLE_COUNTED = "people_counted"
    ENTRY_TO_TABLE = "entry_to_table"
    EXIT_FROM_TABLE = "exit_from_table"
    TABLE_OCCUPIED = "table_occupied"
    TABLE_RELEASED = "table_released"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    TABLE_STATE_CHANGED = "table_state_changed"
    TABLE_PENDING_CLEANING = "table_pending_cleaning"
    TABLE_READY = "table_ready"
    LOW_CONFIDENCE_OBSERVATION = "low_confidence_observation"
    OCCLUSION_SUSPECTED = "occlusion_suspected"
    CAMERA_BLOCKED = "camera_blocked"
    OPERATIONAL_ACTION_RECORDED = "operational_action_recorded"


@dataclass(slots=True)
class CameraStatus:
    camera_id: str
    name: str
    status: str = "online"


@dataclass(slots=True)
class ZoneDefinition:
    zone_id: str
    name: str
    camera_id: str
    polygon_definition: list[list[int]]


@dataclass(slots=True)
class TableDefinition:
    table_id: str
    name: str
    capacity: int
    zone_id: str
    active: bool = True


@dataclass(slots=True)
class TableSession:
    session_id: str
    table_id: str
    start_ts: datetime
    end_ts: datetime | None = None
    people_count_initial: int = 0
    people_count_peak: int = 0
    final_status: str | None = None
    duration_seconds: int | None = None


@dataclass(slots=True)
class DomainEvent:
    event_id: str
    ts: datetime
    camera_id: str
    zone_id: str
    table_id: str | None
    event_type: EventType
    confidence: float
    payload_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TablePrediction:
    prediction_id: str
    ts: datetime
    table_id: str
    model_name: str
    prediction_type: str
    value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    explanation: str


@dataclass(slots=True)
class TableObservation:
    camera_id: str
    zone_id: str
    table_id: str
    people_count: int
    confidence: float
    observed_at: datetime


@dataclass(slots=True)
class TableRuntime:
    table_id: str
    state: TableState = TableState.READY
    last_people_count: int = 0
    people_count_peak: int = 0
    active_session_id: str | None = None
    updated_at: datetime | None = None
    phase: str = "idle"
    needs_attention: bool = False
    assigned_staff: str | None = None
    last_attention_at: datetime | None = None
    operational_note: str | None = None


@dataclass(slots=True)
class TableSnapshot:
    table_id: str
    name: str
    capacity: int
    zone_id: str
    state: TableState
    people_count: int
    people_count_peak: int
    active_session_id: str | None
    updated_at: datetime | None
    phase: str
    needs_attention: bool
    assigned_staff: str | None
    last_attention_at: datetime | None
    operational_note: str | None


@dataclass(slots=True)
class TableOperationalUpdate:
    state: TableState | None = None
    phase: str | None = None
    people_count: int | None = None
    needs_attention: bool | None = None
    assigned_staff: str | None = None
    last_attention_at: datetime | None = None
    operational_note: str | None = None


@dataclass(slots=True)
class OperationalAction:
    action_id: str
    ts: datetime
    action_type: str
    table_id: str | None = None
    queue_group_id: str | None = None
    assigned_staff: str | None = None
    target_channel: str = "shared_panel"
    message: str | None = None
    payload_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ObservationResult:
    table: TableSnapshot
    session: TableSession | None
    events: list[DomainEvent]
    prediction: TablePrediction | None
