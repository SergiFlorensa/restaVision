from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.decision_engine import (
    NextBestActionEngine,
    PromiseEngine,
    QueueGroupSnapshot,
    ServiceContext,
    TableSnapshot,
    calculate_pressure_index,
    score_table_opportunity,
)


def test_pressure_index_enables_critical_service_when_queue_and_occupancy_are_high() -> None:
    now = datetime(2026, 1, 1, 21, 0, tzinfo=UTC)
    context = ServiceContext(
        now=now,
        tables=(
            TableSnapshot("t1", 4, "occupied"),
            TableSnapshot("t2", 4, "finalizing"),
            TableSnapshot("t3", 2, "pending_cleaning"),
            TableSnapshot("t4", 2, "occupied"),
        ),
        queue_groups=(
            QueueGroupSnapshot("q1", 4, now),
            QueueGroupSnapshot("q2", 2, now),
        ),
        p1_alert_count=2,
    )

    pressure = calculate_pressure_index(context)

    assert pressure.mode == "critical_service"
    assert pressure.value >= 75
    assert "cola activa" in pressure.reason


def test_table_opportunity_prefers_ready_compatible_table() -> None:
    now = datetime(2026, 1, 1, 21, 0, tzinfo=UTC)
    table = TableSnapshot("t1", 4, "ready")
    group = QueueGroupSnapshot("q1", 4, now)

    score = score_table_opportunity(table, group)

    assert score.compatible is True
    assert score.score >= 80
    assert score.eta_minutes == 0


def test_promise_engine_returns_conservative_range_for_best_candidate() -> None:
    now = datetime(2026, 1, 1, 21, 0, tzinfo=UTC)
    group = QueueGroupSnapshot("q1", 4, now)
    tables = (
        TableSnapshot("t1", 4, "finalizing", eta_minutes=6),
        TableSnapshot("t2", 6, "occupied", eta_minutes=30),
    )

    promise = PromiseEngine(wait_padding_minutes=2).recommend_wait(group, tables, now)

    assert promise.candidate_table_id == "t1"
    assert promise.wait_min == 9
    assert promise.wait_max == 11
    assert promise.risk == "not_promised"


def test_next_best_action_prioritizes_breached_promise() -> None:
    now = datetime(2026, 1, 1, 21, 12, tzinfo=UTC)
    context = ServiceContext(
        now=now,
        tables=(TableSnapshot("t1", 4, "finalizing", eta_minutes=5),),
        queue_groups=(
            QueueGroupSnapshot(
                "q1",
                4,
                now - timedelta(minutes=15),
                promised_wait_min=8,
                promised_wait_max=10,
                promised_at=now - timedelta(minutes=12),
            ),
        ),
    )

    recommendation = NextBestActionEngine().recommend(context)

    assert recommendation is not None
    assert recommendation.priority == "P1"
    assert "Actualizar espera" in recommendation.answer
    assert "promesa en riesgo" in recommendation.reason
