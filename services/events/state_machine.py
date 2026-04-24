from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import uuid4

from services.events.models import (
    DomainEvent,
    EventType,
    TableDefinition,
    TableObservation,
    TableRuntime,
    TableSession,
    TableState,
    ZoneDefinition,
)


@dataclass(slots=True)
class StateMachineConfig:
    min_seconds_before_finalizing: int = 900
    min_transition_confidence: float = 0.65


@dataclass(slots=True)
class TransitionResult:
    runtime: TableRuntime
    events: list[DomainEvent]
    session_upsert: TableSession | None


class TableStateMachine:
    def __init__(self, config: StateMachineConfig | None = None) -> None:
        self.config = config or StateMachineConfig()

    def apply(
        self,
        table: TableDefinition,
        zone: ZoneDefinition,
        runtime: TableRuntime,
        observation: TableObservation,
        active_session: TableSession | None,
    ) -> TransitionResult:
        runtime = replace(runtime)
        events: list[DomainEvent] = [
            self._event(
                event_type=EventType.PEOPLE_COUNTED,
                observation=observation,
                payload={
                    "people_count": observation.people_count,
                    "previous_people_count": runtime.last_people_count,
                    "table_capacity": table.capacity,
                    "zone_name": zone.name,
                },
            )
        ]

        if observation.confidence < self.config.min_transition_confidence:
            runtime.updated_at = observation.observed_at
            events.append(
                self._event(
                    event_type=EventType.LOW_CONFIDENCE_OBSERVATION,
                    observation=observation,
                    payload={
                        "people_count": observation.people_count,
                        "confidence": observation.confidence,
                        "min_transition_confidence": self.config.min_transition_confidence,
                        "decision": "reject_state_transition",
                    },
                )
            )
            return TransitionResult(runtime=runtime, events=events, session_upsert=None)

        session_upsert = active_session
        previous_state = runtime.state
        previous_count = runtime.last_people_count
        next_state = runtime.state

        if observation.people_count > previous_count and previous_count > 0:
            events.append(
                self._event(
                    event_type=EventType.ENTRY_TO_TABLE,
                    observation=observation,
                    payload={"delta": observation.people_count - previous_count},
                )
            )
        elif observation.people_count < previous_count and observation.people_count > 0:
            events.append(
                self._event(
                    event_type=EventType.EXIT_FROM_TABLE,
                    observation=observation,
                    payload={"delta": previous_count - observation.people_count},
                )
            )

        if observation.people_count > 0 and active_session is None:
            session_upsert = TableSession(
                session_id=self._new_id("ses"),
                table_id=table.table_id,
                start_ts=observation.observed_at,
                people_count_initial=observation.people_count,
                people_count_peak=observation.people_count,
            )
            next_state = TableState.OCCUPIED
            runtime.active_session_id = session_upsert.session_id
            runtime.people_count_peak = observation.people_count
            events.extend(
                [
                    self._event(
                        event_type=EventType.TABLE_OCCUPIED,
                        observation=observation,
                        payload={"people_count": observation.people_count},
                    ),
                    self._event(
                        event_type=EventType.SESSION_STARTED,
                        observation=observation,
                        payload={"session_id": session_upsert.session_id},
                    ),
                ]
            )
        elif observation.people_count == 0 and active_session is not None:
            peak = max(active_session.people_count_peak, runtime.people_count_peak)
            duration_seconds = max(
                int((observation.observed_at - active_session.start_ts).total_seconds()),
                0,
            )
            session_upsert = replace(
                active_session,
                end_ts=observation.observed_at,
                people_count_peak=peak,
                final_status=TableState.PENDING_CLEANING.value,
                duration_seconds=duration_seconds,
            )
            next_state = TableState.PENDING_CLEANING
            runtime.active_session_id = None
            runtime.people_count_peak = 0
            events.extend(
                [
                    self._event(
                        event_type=EventType.TABLE_RELEASED,
                        observation=observation,
                        payload={"session_id": session_upsert.session_id},
                    ),
                    self._event(
                        event_type=EventType.SESSION_ENDED,
                        observation=observation,
                        payload={
                            "session_id": session_upsert.session_id,
                            "duration_seconds": duration_seconds,
                        },
                    ),
                    self._event(
                        event_type=EventType.TABLE_PENDING_CLEANING,
                        observation=observation,
                        payload={"table_id": table.table_id},
                    ),
                ]
            )
        elif observation.people_count > 0 and active_session is not None:
            peak = max(
                active_session.people_count_peak,
                runtime.people_count_peak,
                observation.people_count,
            )
            session_upsert = replace(active_session, people_count_peak=peak)
            runtime.people_count_peak = peak
            if self._should_mark_finalizing(
                active_session=active_session,
                observation=observation,
                previous_people_count=previous_count,
                peak_people_count=peak,
            ):
                next_state = TableState.FINALIZING
            elif previous_state in {TableState.FINALIZING, TableState.PAYMENT} and (
                observation.people_count >= previous_count
            ):
                next_state = TableState.OCCUPIED
            elif previous_state in {TableState.READY, TableState.PENDING_CLEANING}:
                next_state = TableState.OCCUPIED

        runtime.state = next_state
        runtime.last_people_count = observation.people_count
        runtime.updated_at = observation.observed_at

        if next_state != previous_state:
            events.append(
                self._event(
                    event_type=EventType.TABLE_STATE_CHANGED,
                    observation=observation,
                    payload={
                        "from_state": previous_state.value,
                        "to_state": next_state.value,
                    },
                )
            )

        return TransitionResult(runtime=runtime, events=events, session_upsert=session_upsert)

    def _should_mark_finalizing(
        self,
        active_session: TableSession,
        observation: TableObservation,
        previous_people_count: int,
        peak_people_count: int,
    ) -> bool:
        elapsed_seconds = int((observation.observed_at - active_session.start_ts).total_seconds())
        if elapsed_seconds < self.config.min_seconds_before_finalizing:
            return False
        if observation.people_count >= previous_people_count:
            return False
        return observation.people_count < peak_people_count

    def _event(
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
