from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Full, Queue
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class RealtimeEvent:
    event_type: str
    payload: dict[str, Any]
    event_id: str | None = None


@dataclass(frozen=True, slots=True)
class RealtimeSubscription:
    queue: Queue[RealtimeEvent]

    def get(self, timeout_seconds: float) -> RealtimeEvent | None:
        try:
            return self.queue.get(timeout=timeout_seconds)
        except Empty:
            return None


class RealtimeEventBus:
    """Thread-safe in-process event bus for local dashboard updates.

    It is intentionally lightweight: one FastAPI process, small JSON payloads,
    no broker, no heavy dependency. If a subscriber is slow, old messages are
    dropped so the dashboard receives the latest operational state instead of a
    stale backlog.
    """

    def __init__(self, max_queue_size: int = 100) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be >= 1")
        self._max_queue_size = max_queue_size
        self._subscribers: set[RealtimeSubscription] = set()
        self._lock = Lock()

    def subscribe(self) -> RealtimeSubscription:
        subscription = RealtimeSubscription(Queue(maxsize=self._max_queue_size))
        with self._lock:
            self._subscribers.add(subscription)
        return subscription

    def unsubscribe(self, subscription: RealtimeSubscription) -> None:
        with self._lock:
            self._subscribers.discard(subscription)

    def publish(self, event: RealtimeEvent) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers)
        for subscription in subscribers:
            self._publish_to_subscription(subscription, event)

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def _publish_to_subscription(
        self,
        subscription: RealtimeSubscription,
        event: RealtimeEvent,
    ) -> None:
        try:
            subscription.queue.put_nowait(event)
            return
        except Full:
            self._drop_oldest(subscription)
        try:
            subscription.queue.put_nowait(event)
        except Full:
            return

    @staticmethod
    def _drop_oldest(subscription: RealtimeSubscription) -> None:
        try:
            subscription.queue.get_nowait()
        except Empty:
            return
