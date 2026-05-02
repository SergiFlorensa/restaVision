from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class TableState(StrEnum):
    READY = "ready"
    OCCUPIED = "occupied"
    EATING = "eating"
    FINALIZING = "finalizing"
    PENDING_CLEANING = "pending_cleaning"
    BLOCKED = "blocked"
    NEEDS_ATTENTION = "needs_attention"
    UNKNOWN = "unknown"


class QueueGroupStatus(StrEnum):
    WAITING = "waiting"
    SEATED = "seated"
    ABANDONED = "abandoned"


@dataclass(frozen=True, slots=True)
class TableSnapshot:
    table_id: str
    capacity: int
    state: str
    active_session_minutes: float = 0.0
    eta_minutes: float | None = None
    zone_id: str | None = None
    needs_attention: bool = False


@dataclass(frozen=True, slots=True)
class QueueGroupSnapshot:
    queue_group_id: str
    party_size: int
    arrival_ts: datetime
    status: str = QueueGroupStatus.WAITING
    promised_wait_min: int | None = None
    promised_wait_max: int | None = None
    promised_at: datetime | None = None
    preferred_zone_id: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceContext:
    now: datetime
    tables: tuple[TableSnapshot, ...] = ()
    queue_groups: tuple[QueueGroupSnapshot, ...] = ()
    p1_alert_count: int = 0
    staff_shortage: bool = False


@dataclass(frozen=True, slots=True)
class PressureIndex:
    value: int
    mode: str
    reason: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpportunityScore:
    table_id: str
    score: int
    compatible: bool
    eta_minutes: float | None
    reason: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PromiseRecommendation:
    queue_group_id: str
    candidate_table_id: str | None
    wait_min: int
    wait_max: int
    confidence: float
    risk: str
    message: str
    reason: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DecisionRecommendation:
    decision_id: str
    mode: str
    priority: str
    question: str
    answer: str
    confidence: float
    impact: str
    table_id: str | None = None
    queue_group_id: str | None = None
    eta_minutes: float | None = None
    reason: tuple[str, ...] = ()
    expires_in_seconds: int = 180
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionFeedback:
    feedback_id: str
    decision_id: str
    ts: datetime
    feedback_type: str
    accepted: bool
    useful: bool | None = None
    outcome: dict[str, object] = field(default_factory=dict)
    comment: str | None = None
