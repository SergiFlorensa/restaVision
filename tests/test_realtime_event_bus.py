from __future__ import annotations

from services.events.realtime import RealtimeEvent, RealtimeEventBus


def test_realtime_event_bus_delivers_to_subscribers() -> None:
    bus = RealtimeEventBus(max_queue_size=2)
    subscription = bus.subscribe()

    bus.publish(
        RealtimeEvent(
            event_type="table_service_analysis",
            event_id="table_01:1",
            payload={"table_id": "table_01", "state": "seated"},
        )
    )

    event = subscription.get(timeout_seconds=0.1)
    assert event is not None
    assert event.event_type == "table_service_analysis"
    assert event.payload["table_id"] == "table_01"

    bus.unsubscribe(subscription)
    assert bus.subscriber_count() == 0


def test_realtime_event_bus_drops_oldest_when_subscriber_is_slow() -> None:
    bus = RealtimeEventBus(max_queue_size=1)
    subscription = bus.subscribe()

    bus.publish(RealtimeEvent(event_type="demo", event_id="old", payload={"value": "old"}))
    bus.publish(RealtimeEvent(event_type="demo", event_id="new", payload={"value": "new"}))

    event = subscription.get(timeout_seconds=0.1)
    assert event is not None
    assert event.event_id == "new"
