from __future__ import annotations

import csv

from services.monitoring.latency import LatencyTracker


def test_latency_tracker_discards_warmup_samples_and_calculates_percentiles() -> None:
    tracker = LatencyTracker(warmup_samples=2)

    assert not tracker.record("inference", 100)
    assert not tracker.record("inference", 80)
    assert tracker.record("inference", 10)
    assert tracker.record("inference", 20)
    assert tracker.record("inference", 30)

    summary = tracker.summary_for("inference")

    assert summary.sample_count == 3
    assert summary.p50_ms == 20
    assert summary.p99_ms > summary.p95_ms
    assert summary.max_ms == 30


def test_latency_tracker_exports_samples_to_csv(tmp_path) -> None:
    tracker = LatencyTracker()
    tracker.record(
        stage="pipeline",
        duration_ms=12.5,
        frame_index=7,
        model_version="yolo11n_int8_v1",
        cpu_temperature_c=62.0,
    )
    target = tmp_path / "latency.csv"

    tracker.export_csv(target)

    with target.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "stage": "pipeline",
            "duration_ms": "12.5",
            "frame_index": "7",
            "model_version": "yolo11n_int8_v1",
            "cpu_temperature_c": "62.0",
        }
    ]
