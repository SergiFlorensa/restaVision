from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from services.vision.geometry import ScoredDetection

CUTLERY_LABELS: tuple[str, ...] = ("fork", "knife", "spoon")
EMPTY_PLATE_LABELS: tuple[str, ...] = ("plate_empty",)
FULL_PLATE_LABELS: tuple[str, ...] = ("plate_full",)
SEMANTIC_PLATE_LABELS: tuple[str, ...] = EMPTY_PLATE_LABELS + FULL_PLATE_LABELS
PLATE_LABELS: tuple[str, ...] = ("plate", "bowl") + SEMANTIC_PLATE_LABELS
FOOD_LABELS: tuple[str, ...] = (
    "pizza",
    "sandwich",
    "hot dog",
    "cake",
    "donut",
    "banana",
    "apple",
    "orange",
    "broccoli",
    "carrot",
    "bowl",
)
ATTENTION_LABELS: tuple[str, ...] = (
    "hand_raised",
    "raised_hand",
    "finger_raised",
    "call_waiter",
)
SERVICE_RELEVANT_LABELS: tuple[str, ...] = tuple(
    sorted(
        set(
            (
                "person",
                "chair",
                "dining table",
                "cup",
                "bottle",
                "wine glass",
            )
            + CUTLERY_LABELS
            + PLATE_LABELS
            + FOOD_LABELS
            + ATTENTION_LABELS
        )
    )
)


@dataclass(frozen=True, slots=True)
class TableServiceMonitorConfig:
    """Configurable service rules for one demo table.

    The first version is intentionally local-first and non-invasive. It does not
    identify customers; it only reasons about table objects and anonymous people.
    """

    table_id: str = "table_01"
    require_plate: bool = True
    require_fork: bool = True
    require_knife: bool = True
    require_spoon: bool = False
    min_people_for_service_check: int = 1
    alert_cooldown_seconds: int = 12
    max_timeline_events: int = 30
    finishing_empty_plate_ratio: float = 0.5
    dirty_grace_seconds: int = 180

    def __post_init__(self) -> None:
        if not 0 < self.finishing_empty_plate_ratio <= 1:
            raise ValueError("finishing_empty_plate_ratio must be between 0 and 1.")
        if self.dirty_grace_seconds < 0:
            raise ValueError("dirty_grace_seconds must be >= 0.")


@dataclass(slots=True)
class ServiceAlert:
    alert_id: str
    ts: datetime
    alert_type: str
    severity: str
    message: str
    evidence: dict[str, Any]
    active: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "ts": self.ts,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "active": self.active,
        }


@dataclass(slots=True)
class ServiceTimelineEvent:
    event_id: str
    ts: datetime
    event_type: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "ts": self.ts,
            "event_type": self.event_type,
            "message": self.message,
            "payload": self.payload,
        }


@dataclass(slots=True)
class TableServiceAnalysis:
    table_id: str
    updated_at: datetime
    state: str
    people_count: int
    object_counts: dict[str, int]
    missing_items: dict[str, int]
    service_flags: dict[str, bool]
    active_alerts: list[ServiceAlert]
    timeline_events: list[ServiceTimelineEvent]
    seat_duration_seconds: int | None
    away_duration_seconds: int | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "updated_at": self.updated_at,
            "state": self.state,
            "people_count": self.people_count,
            "object_counts": self.object_counts,
            "missing_items": self.missing_items,
            "service_flags": self.service_flags,
            "active_alerts": [alert.to_payload() for alert in self.active_alerts],
            "timeline_events": [event.to_payload() for event in self.timeline_events],
            "seat_duration_seconds": self.seat_duration_seconds,
            "away_duration_seconds": self.away_duration_seconds,
        }


class TableServiceMonitor:
    """Stateful table-service analyzer for the dinner/webcam demo.

    It transforms raw YOLO detections into operational table signals:
    missing setup, food served, plate removal, customer attention and away/return.
    This is a lightweight bridge between computer vision and dashboard UX.
    """

    def __init__(self, config: TableServiceMonitorConfig | None = None) -> None:
        self.config = config or TableServiceMonitorConfig()
        self._timeline: deque[ServiceTimelineEvent] = deque(maxlen=self.config.max_timeline_events)
        self._last_event_ts_by_type: dict[str, datetime] = {}
        self._first_seen_at: datetime | None = None
        self._last_seen_at: datetime | None = None
        self._away_started_at: datetime | None = None
        self._previous_people_count = 0
        self._previous_plate_count = 0
        self._previous_food_count = 0
        self._previous_state = "waiting_for_video"
        self._latest_analysis = self._build_empty_analysis(datetime.now(UTC))

    def process(
        self,
        detections: list[ScoredDetection],
        observed_at: datetime | None = None,
        stable_counts: dict[str, int] | None = None,
    ) -> TableServiceAnalysis:
        ts = observed_at or datetime.now(UTC)
        counts = dict(sorted((stable_counts or count_labels(detections)).items()))
        people_count = counts.get("person", 0)
        plate_count = count_matching_labels(counts, PLATE_LABELS)
        food_count = count_matching_labels(counts, FOOD_LABELS)
        cutlery_count = count_matching_labels(counts, CUTLERY_LABELS)
        attention_count = count_matching_labels(counts, ATTENTION_LABELS)
        empty_plate_count = count_matching_labels(counts, EMPTY_PLATE_LABELS)
        full_plate_count = count_matching_labels(counts, FULL_PLATE_LABELS)
        semantic_plate_count = empty_plate_count + full_plate_count
        empty_plate_ratio = (
            empty_plate_count / semantic_plate_count if semantic_plate_count > 0 else 0.0
        )

        self._update_presence_state(people_count, ts)
        self._register_transition_events(
            people_count=people_count,
            plate_count=plate_count,
            food_count=food_count,
            attention_count=attention_count,
            counts=counts,
            ts=ts,
        )

        missing_items = self._calculate_missing_items(people_count, counts)
        service_flags = {
            "plates_complete": missing_items.get("plate", 0) == 0,
            "cutlery_complete": not any(
                missing_items.get(label, 0) > 0 for label in CUTLERY_LABELS
            ),
            "food_served": food_count > 0,
            "customer_needs_attention": attention_count > 0,
            "semantic_plate_state_known": semantic_plate_count > 0,
            "plates_empty_majority": (
                semantic_plate_count > 0
                and empty_plate_ratio >= self.config.finishing_empty_plate_ratio
            ),
        }
        state = self._classify_state(
            people_count=people_count,
            plate_count=plate_count,
            food_count=food_count,
            cutlery_count=cutlery_count,
            empty_plate_count=empty_plate_count,
            full_plate_count=full_plate_count,
            empty_plate_ratio=empty_plate_ratio,
            missing_items=missing_items,
            ts=ts,
        )
        service_flags["ready_for_checkout"] = state == "finishing"
        service_flags["needs_cleaning"] = state == "dirty"
        self._register_state_event(state=state, counts=counts, ts=ts)
        active_alerts = self._build_active_alerts(
            state=state,
            people_count=people_count,
            missing_items=missing_items,
            service_flags=service_flags,
            counts=counts,
            ts=ts,
        )
        analysis = TableServiceAnalysis(
            table_id=self.config.table_id,
            updated_at=ts,
            state=state,
            people_count=people_count,
            object_counts=counts,
            missing_items=missing_items,
            service_flags=service_flags,
            active_alerts=active_alerts,
            timeline_events=list(self._timeline),
            seat_duration_seconds=self._seat_duration_seconds(ts),
            away_duration_seconds=self._away_duration_seconds(ts),
        )
        self._latest_analysis = analysis
        self._previous_people_count = people_count
        self._previous_plate_count = plate_count
        self._previous_food_count = food_count
        self._previous_state = state
        return analysis

    def current(self) -> TableServiceAnalysis:
        return self._latest_analysis

    def _update_presence_state(self, people_count: int, ts: datetime) -> None:
        if people_count > 0:
            if self._first_seen_at is None:
                self._first_seen_at = ts
            self._last_seen_at = ts
            if self._away_started_at is not None:
                away_seconds = int((ts - self._away_started_at).total_seconds())
                self._emit_event(
                    "customer_returned",
                    "Cliente vuelve a la mesa",
                    ts,
                    {"away_duration_seconds": away_seconds},
                )
                self._away_started_at = None
        elif self._previous_people_count > 0 and self._away_started_at is None:
            self._away_started_at = ts
            self._emit_event(
                "customer_left_table",
                "Cliente se levanta o abandona temporalmente la mesa",
                ts,
                {},
            )

    def _register_transition_events(
        self,
        people_count: int,
        plate_count: int,
        food_count: int,
        attention_count: int,
        counts: dict[str, int],
        ts: datetime,
    ) -> None:
        if self._previous_people_count == 0 and people_count > 0:
            self._emit_event(
                "table_session_started",
                "Cliente detectado en la mesa",
                ts,
                {"people_count": people_count},
            )
        if self._previous_plate_count == 0 and plate_count > 0:
            self._emit_event(
                "plate_served",
                "Plato o recipiente detectado en mesa",
                ts,
                {"plate_like_objects": plate_count},
            )
        if self._previous_food_count == 0 and food_count > 0:
            self._emit_event(
                "food_served",
                "Comida detectada en mesa",
                ts,
                {"food_like_objects": food_count},
            )
        if self._previous_plate_count > 0 and plate_count == 0:
            self._emit_event("plate_removed", "Retirada de plato detectada", ts, {})
        if attention_count > 0:
            self._emit_event(
                "customer_attention_requested",
                "Posible gesto de llamada o mano levantada",
                ts,
                {"attention_labels": matching_counts(counts, ATTENTION_LABELS)},
                cooldown=True,
            )

    def _calculate_missing_items(
        self,
        people_count: int,
        counts: dict[str, int],
    ) -> dict[str, int]:
        if people_count < self.config.min_people_for_service_check:
            return {}

        missing: dict[str, int] = {}
        if self.config.require_plate:
            available_plates = count_matching_labels(counts, PLATE_LABELS)
            missing["plate"] = max(0, people_count - available_plates)
        if self.config.require_fork:
            missing["fork"] = max(0, people_count - counts.get("fork", 0))
        if self.config.require_knife:
            missing["knife"] = max(0, people_count - counts.get("knife", 0))
        if self.config.require_spoon:
            missing["spoon"] = max(0, people_count - counts.get("spoon", 0))
        return {label: value for label, value in missing.items() if value > 0}

    def _build_active_alerts(
        self,
        state: str,
        people_count: int,
        missing_items: dict[str, int],
        service_flags: dict[str, bool],
        counts: dict[str, int],
        ts: datetime,
    ) -> list[ServiceAlert]:
        alerts: list[ServiceAlert] = []
        if state == "dirty":
            alerts.append(
                ServiceAlert(
                    alert_id=f"{self.config.table_id}_dirty",
                    ts=ts,
                    alert_type="table_dirty",
                    severity="high",
                    message="Mesa pendiente de limpieza",
                    evidence={"object_counts": counts},
                )
            )
        if state == "finishing":
            alerts.append(
                ServiceAlert(
                    alert_id=f"{self.config.table_id}_finishing",
                    ts=ts,
                    alert_type="table_finishing",
                    severity="medium",
                    message="Cliente posiblemente ha terminado",
                    evidence={"object_counts": counts},
                )
            )
        if people_count > 0 and missing_items:
            message = build_missing_setup_message(missing_items)
            alerts.append(
                ServiceAlert(
                    alert_id=f"{self.config.table_id}_missing_setup",
                    ts=ts,
                    alert_type="missing_table_setup",
                    severity="medium",
                    message=message,
                    evidence={"missing_items": missing_items, "people_count": people_count},
                )
            )
            self._emit_event(
                "missing_table_setup",
                message,
                ts,
                {"missing_items": missing_items, "people_count": people_count},
                cooldown=True,
            )

        if service_flags["customer_needs_attention"]:
            alerts.append(
                ServiceAlert(
                    alert_id=f"{self.config.table_id}_attention",
                    ts=ts,
                    alert_type="customer_attention_requested",
                    severity="high",
                    message="Posible cliente solicitando atención",
                    evidence={"attention_labels": matching_counts(counts, ATTENTION_LABELS)},
                )
            )
        return alerts

    def _classify_state(
        self,
        people_count: int,
        plate_count: int,
        food_count: int,
        cutlery_count: int,
        empty_plate_count: int,
        full_plate_count: int,
        empty_plate_ratio: float,
        missing_items: dict[str, int],
        ts: datetime,
    ) -> str:
        service_residue_count = plate_count + cutlery_count + food_count
        semantic_plate_known = empty_plate_count + full_plate_count > 0
        mostly_empty = (
            semantic_plate_known and empty_plate_ratio >= self.config.finishing_empty_plate_ratio
        )
        dirty_evidence = (
            empty_plate_count > 0
            or (not semantic_plate_known and service_residue_count > 0)
            or food_count > 0
        )

        if people_count == 0 and service_residue_count == 0:
            return "empty"
        if people_count == 0 and self._away_started_at is not None:
            if dirty_evidence and self._dirty_grace_elapsed(ts):
                return "dirty"
            return "away"
        if people_count == 0 and dirty_evidence:
            return "observing"
        if people_count > 0 and mostly_empty:
            return "finishing"
        if people_count > 0 and food_count > 0:
            return "eating"
        if people_count > 0 and full_plate_count > 0:
            return "eating"
        if people_count > 0 and missing_items:
            return "needs_setup"
        if people_count > 0:
            return "seated"
        return "observing"

    def _seat_duration_seconds(self, ts: datetime) -> int | None:
        if self._first_seen_at is None:
            return None
        return max(0, int((ts - self._first_seen_at).total_seconds()))

    def _away_duration_seconds(self, ts: datetime) -> int | None:
        if self._away_started_at is None:
            return None
        return max(0, int((ts - self._away_started_at).total_seconds()))

    def _dirty_grace_elapsed(self, ts: datetime) -> bool:
        if self._away_started_at is None:
            return False
        elapsed = (ts - self._away_started_at).total_seconds()
        return elapsed >= self.config.dirty_grace_seconds

    def _register_state_event(self, state: str, counts: dict[str, int], ts: datetime) -> None:
        if state == self._previous_state:
            return
        if self._previous_state == "waiting_for_video" and state in {"empty", "observing"}:
            return
        self._emit_event(
            "table_state_changed",
            state_change_message(state),
            ts,
            {
                "previous_state": self._previous_state,
                "new_state": state,
                "object_counts": counts,
            },
        )
        if state == "dirty":
            self._emit_event(
                "table_dirty",
                "Mesa pendiente de limpieza",
                ts,
                {"object_counts": counts},
            )
        if state == "finishing":
            self._emit_event(
                "table_finishing",
                "Cliente posiblemente ha terminado",
                ts,
                {"object_counts": counts},
            )

    def _emit_event(
        self,
        event_type: str,
        message: str,
        ts: datetime,
        payload: dict[str, Any],
        cooldown: bool = False,
    ) -> None:
        if cooldown and not self._can_emit(event_type, ts):
            return
        self._last_event_ts_by_type[event_type] = ts
        event = ServiceTimelineEvent(
            event_id=f"{self.config.table_id}_{event_type}_{int(ts.timestamp())}",
            ts=ts,
            event_type=event_type,
            message=message,
            payload=payload,
        )
        self._timeline.appendleft(event)

    def _can_emit(self, event_type: str, ts: datetime) -> bool:
        previous = self._last_event_ts_by_type.get(event_type)
        if previous is None:
            return True
        elapsed = (ts - previous).total_seconds()
        return elapsed >= self.config.alert_cooldown_seconds

    def _build_empty_analysis(self, ts: datetime) -> TableServiceAnalysis:
        return TableServiceAnalysis(
            table_id=self.config.table_id,
            updated_at=ts,
            state="waiting_for_video",
            people_count=0,
            object_counts={},
            missing_items={},
            service_flags={
                "plates_complete": False,
                "cutlery_complete": False,
                "food_served": False,
                "customer_needs_attention": False,
                "semantic_plate_state_known": False,
                "plates_empty_majority": False,
                "ready_for_checkout": False,
                "needs_cleaning": False,
            },
            active_alerts=[],
            timeline_events=[],
            seat_duration_seconds=None,
            away_duration_seconds=None,
        )


def count_labels(detections: list[ScoredDetection]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        label = detection.label or "object"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def count_matching_labels(counts: dict[str, int], labels: tuple[str, ...]) -> int:
    return sum(counts.get(label, 0) for label in labels)


def matching_counts(counts: dict[str, int], labels: tuple[str, ...]) -> dict[str, int]:
    return {label: counts[label] for label in labels if counts.get(label, 0) > 0}


def build_missing_setup_message(missing_items: dict[str, int]) -> str:
    if not missing_items:
        return "Servicio de mesa completo"
    parts = [f"{label}: {amount}" for label, amount in sorted(missing_items.items())]
    return "Falta completar servicio de mesa — " + ", ".join(parts)


def state_change_message(state: str) -> str:
    messages = {
        "away": "Cliente se ausenta de la mesa",
        "dirty": "Mesa pendiente de limpieza",
        "eating": "Cliente comiendo",
        "empty": "Mesa vacía",
        "finishing": "Cliente posiblemente ha terminado",
        "needs_setup": "Servicio de mesa incompleto",
        "observing": "Mesa en observación",
        "seated": "Cliente sentado",
    }
    return messages.get(state, f"Estado de mesa: {state}")
