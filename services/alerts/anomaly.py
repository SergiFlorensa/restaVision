from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from math import erfc, sqrt
from statistics import fmean, pstdev
from typing import Any
from uuid import uuid4

from services.events.models import TableSession


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"


class OperationalAlertType(StrEnum):
    LONG_SESSION_ATTENTION = "long_session_attention"


@dataclass(slots=True)
class OperationalAlert:
    alert_id: str
    ts: datetime
    table_id: str
    session_id: str | None
    alert_type: OperationalAlertType
    severity: AlertSeverity
    message: str
    score: float
    evidence_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DurationStats:
    sample_count: int
    mean_seconds: float
    std_seconds: float


@dataclass(slots=True)
class DurationAnomalyConfig:
    min_samples: int = 5
    z_threshold: float = 2.0
    min_current_duration_seconds: int = 900
    min_absolute_margin_seconds: int = 300


class OperationalAnomalyDetector:
    """Detects soft operational alerts from already available MVP signals."""

    def __init__(self, config: DurationAnomalyConfig | None = None) -> None:
        self.config = config or DurationAnomalyConfig()

    def detect_long_session(
        self,
        table_id: str,
        active_session: TableSession,
        historical_sessions: list[TableSession],
        now: datetime,
    ) -> OperationalAlert | None:
        stats = self.build_duration_stats(historical_sessions)
        if stats is None:
            return None

        elapsed_seconds = max(int((now - active_session.start_ts).total_seconds()), 0)
        if elapsed_seconds < self.config.min_current_duration_seconds:
            return None

        threshold_seconds = self._threshold(stats)
        if elapsed_seconds <= threshold_seconds:
            return None

        overage_seconds = elapsed_seconds - threshold_seconds
        z_score = (
            (elapsed_seconds - stats.mean_seconds) / stats.std_seconds
            if stats.std_seconds > 0
            else None
        )
        tail_probability = self._one_sided_tail_probability(z_score)
        score = min(1.0, overage_seconds / max(threshold_seconds, 1.0))

        evidence: dict[str, Any] = {
            "elapsed_seconds": elapsed_seconds,
            "threshold_seconds": round(threshold_seconds, 2),
            "historical_sample_count": stats.sample_count,
            "historical_mean_seconds": round(stats.mean_seconds, 2),
            "historical_std_seconds": round(stats.std_seconds, 2),
            "overage_seconds": round(overage_seconds, 2),
        }
        if z_score is not None:
            evidence["z_score"] = round(z_score, 4)
        if tail_probability is not None:
            evidence["normal_tail_probability"] = round(tail_probability, 6)

        return OperationalAlert(
            alert_id=f"alert_{uuid4().hex[:12]}",
            ts=now,
            table_id=table_id,
            session_id=active_session.session_id,
            alert_type=OperationalAlertType.LONG_SESSION_ATTENTION,
            severity=AlertSeverity.WARNING,
            message=(
                "Mesa con duracion fuera del rango esperado; revisar si necesita "
                "atencion operativa."
            ),
            score=round(score, 4),
            evidence_json=evidence,
        )

    def build_duration_stats(self, historical_sessions: list[TableSession]) -> DurationStats | None:
        durations = [
            float(session.duration_seconds)
            for session in historical_sessions
            if session.duration_seconds is not None and session.duration_seconds > 0
        ]
        if len(durations) < self.config.min_samples:
            return None

        return DurationStats(
            sample_count=len(durations),
            mean_seconds=float(fmean(durations)),
            std_seconds=float(pstdev(durations)) if len(durations) > 1 else 0.0,
        )

    def _threshold(self, stats: DurationStats) -> float:
        statistical_margin = self.config.z_threshold * stats.std_seconds
        minimum_margin = float(self.config.min_absolute_margin_seconds)
        return stats.mean_seconds + max(statistical_margin, minimum_margin)

    @staticmethod
    def _one_sided_tail_probability(z_score: float | None) -> float | None:
        if z_score is None:
            return None
        return 0.5 * erfc(z_score / sqrt(2.0))
