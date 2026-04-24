from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Self

import numpy as np


@dataclass(frozen=True, slots=True)
class LatencySample:
    stage: str
    duration_ms: float
    frame_index: int | None = None
    model_version: str | None = None
    cpu_temperature_c: float | None = None


@dataclass(frozen=True, slots=True)
class LatencySummary:
    stage: str
    sample_count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    std_ms: float
    min_ms: float
    max_ms: float

    @property
    def jitter_ms(self) -> float:
        return self.std_ms


class LatencyTracker:
    def __init__(self, warmup_samples: int = 0) -> None:
        if warmup_samples < 0:
            raise ValueError("warmup_samples must be non-negative.")
        self.warmup_samples = warmup_samples
        self._seen_by_stage: dict[str, int] = defaultdict(int)
        self._samples: list[LatencySample] = []

    def record(
        self,
        stage: str,
        duration_ms: float,
        frame_index: int | None = None,
        model_version: str | None = None,
        cpu_temperature_c: float | None = None,
    ) -> bool:
        if not stage:
            raise ValueError("stage must not be empty.")
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative.")

        self._seen_by_stage[stage] += 1
        if self._seen_by_stage[stage] <= self.warmup_samples:
            return False

        self._samples.append(
            LatencySample(
                stage=stage,
                duration_ms=duration_ms,
                frame_index=frame_index,
                model_version=model_version,
                cpu_temperature_c=cpu_temperature_c,
            )
        )
        return True

    def measure(
        self,
        stage: str,
        frame_index: int | None = None,
        model_version: str | None = None,
        cpu_temperature_c: float | None = None,
    ) -> LatencyMeasurement:
        return LatencyMeasurement(
            tracker=self,
            stage=stage,
            frame_index=frame_index,
            model_version=model_version,
            cpu_temperature_c=cpu_temperature_c,
        )

    def summaries(self) -> list[LatencySummary]:
        samples_by_stage: dict[str, list[float]] = defaultdict(list)
        for sample in self._samples:
            samples_by_stage[sample.stage].append(sample.duration_ms)

        return [
            _summary(stage=stage, values=np.asarray(values, dtype=float))
            for stage, values in sorted(samples_by_stage.items())
        ]

    def summary_for(self, stage: str) -> LatencySummary:
        values = [sample.duration_ms for sample in self._samples if sample.stage == stage]
        if not values:
            raise ValueError(f"No latency samples recorded for stage: {stage}")
        return _summary(stage=stage, values=np.asarray(values, dtype=float))

    def export_csv(self, path: str | Path) -> None:
        target = Path(path)
        if target.parent != Path("."):
            target.parent.mkdir(parents=True, exist_ok=True)

        with target.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "stage",
                    "duration_ms",
                    "frame_index",
                    "model_version",
                    "cpu_temperature_c",
                ],
            )
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(
                    {
                        "stage": sample.stage,
                        "duration_ms": sample.duration_ms,
                        "frame_index": sample.frame_index,
                        "model_version": sample.model_version,
                        "cpu_temperature_c": sample.cpu_temperature_c,
                    }
                )

    @property
    def samples(self) -> list[LatencySample]:
        return list(self._samples)


class LatencyMeasurement:
    def __init__(
        self,
        tracker: LatencyTracker,
        stage: str,
        frame_index: int | None,
        model_version: str | None,
        cpu_temperature_c: float | None,
    ) -> None:
        self.tracker = tracker
        self.stage = stage
        self.frame_index = frame_index
        self.model_version = model_version
        self.cpu_temperature_c = cpu_temperature_c
        self._started_at: float | None = None

    def __enter__(self) -> Self:
        self._started_at = perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        if self._started_at is None:
            raise RuntimeError("LatencyMeasurement was not started.")
        duration_ms = (perf_counter() - self._started_at) * 1000
        self.tracker.record(
            stage=self.stage,
            duration_ms=duration_ms,
            frame_index=self.frame_index,
            model_version=self.model_version,
            cpu_temperature_c=self.cpu_temperature_c,
        )


def _summary(stage: str, values: np.ndarray) -> LatencySummary:
    if values.size == 0:
        raise ValueError("values must not be empty.")
    return LatencySummary(
        stage=stage,
        sample_count=int(values.size),
        mean_ms=float(np.mean(values)),
        p50_ms=float(np.percentile(values, 50)),
        p95_ms=float(np.percentile(values, 95)),
        p99_ms=float(np.percentile(values, 99)),
        std_ms=float(np.std(values)),
        min_ms=float(np.min(values)),
        max_ms=float(np.max(values)),
    )
