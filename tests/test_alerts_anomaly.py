from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.alerts.anomaly import DurationAnomalyConfig, OperationalAnomalyDetector
from services.events.models import TableSession


def make_completed_session(index: int, duration_seconds: int) -> TableSession:
    start = datetime(2026, 4, 13, 12, 0, tzinfo=UTC) + timedelta(days=index)
    return TableSession(
        session_id=f"ses_done_{index}",
        table_id="table_01",
        start_ts=start,
        end_ts=start + timedelta(seconds=duration_seconds),
        people_count_initial=2,
        people_count_peak=2,
        final_status="pending_cleaning",
        duration_seconds=duration_seconds,
    )


def make_active_session(start: datetime) -> TableSession:
    return TableSession(
        session_id="ses_active",
        table_id="table_01",
        start_ts=start,
        people_count_initial=2,
        people_count_peak=2,
    )


def test_detector_skips_alert_until_minimum_history_exists() -> None:
    detector = OperationalAnomalyDetector(
        DurationAnomalyConfig(min_samples=5, min_current_duration_seconds=0)
    )
    active_session = make_active_session(datetime(2026, 4, 20, 12, 0, tzinfo=UTC))

    alert = detector.detect_long_session(
        table_id="table_01",
        active_session=active_session,
        historical_sessions=[make_completed_session(1, 1800)],
        now=active_session.start_ts + timedelta(hours=2),
    )

    assert alert is None


def test_detector_skips_session_inside_expected_duration_range() -> None:
    detector = OperationalAnomalyDetector(
        DurationAnomalyConfig(min_samples=5, z_threshold=2.0, min_current_duration_seconds=0)
    )
    active_session = make_active_session(datetime(2026, 4, 20, 12, 0, tzinfo=UTC))
    history = [make_completed_session(index, duration) for index, duration in enumerate([1700] * 5)]

    alert = detector.detect_long_session(
        table_id="table_01",
        active_session=active_session,
        historical_sessions=history,
        now=active_session.start_ts + timedelta(seconds=1900),
    )

    assert alert is None


def test_detector_alerts_when_session_exceeds_statistical_threshold() -> None:
    detector = OperationalAnomalyDetector(
        DurationAnomalyConfig(
            min_samples=5,
            z_threshold=2.0,
            min_current_duration_seconds=0,
            min_absolute_margin_seconds=60,
        )
    )
    active_session = make_active_session(datetime(2026, 4, 20, 12, 0, tzinfo=UTC))
    history = [
        make_completed_session(index, duration)
        for index, duration in enumerate([1700, 1800, 1900, 2000, 2100])
    ]

    alert = detector.detect_long_session(
        table_id="table_01",
        active_session=active_session,
        historical_sessions=history,
        now=active_session.start_ts + timedelta(seconds=2600),
    )

    assert alert is not None
    assert alert.alert_type == "long_session_attention"
    assert alert.severity == "warning"
    assert alert.evidence_json["historical_sample_count"] == 5
    assert "z_score" in alert.evidence_json
    assert "normal_tail_probability" in alert.evidence_json


def test_detector_uses_minimum_margin_when_history_has_zero_variance() -> None:
    detector = OperationalAnomalyDetector(
        DurationAnomalyConfig(
            min_samples=5,
            z_threshold=2.0,
            min_current_duration_seconds=0,
            min_absolute_margin_seconds=120,
        )
    )
    active_session = make_active_session(datetime(2026, 4, 20, 12, 0, tzinfo=UTC))
    history = [make_completed_session(index, 1800) for index in range(5)]

    alert = detector.detect_long_session(
        table_id="table_01",
        active_session=active_session,
        historical_sessions=history,
        now=active_session.start_ts + timedelta(seconds=2000),
    )

    assert alert is not None
    assert alert.evidence_json["threshold_seconds"] == 1920.0
    assert "z_score" not in alert.evidence_json
