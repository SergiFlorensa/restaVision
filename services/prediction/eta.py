from __future__ import annotations

from datetime import datetime
from statistics import mean, pstdev
from uuid import uuid4

from services.events.models import TablePrediction, TableSession


class EtaBaselineService:
    def __init__(self, default_session_duration_seconds: int = 3600) -> None:
        self.default_session_duration_seconds = default_session_duration_seconds

    def predict(
        self,
        table_id: str,
        active_session: TableSession,
        historical_sessions: list[TableSession],
        now: datetime,
    ) -> TablePrediction:
        completed_durations = [
            session.duration_seconds
            for session in historical_sessions
            if session.duration_seconds is not None and session.duration_seconds > 0
        ]
        if completed_durations:
            baseline_duration = float(mean(completed_durations))
            spread = float(pstdev(completed_durations)) if len(completed_durations) > 1 else baseline_duration * 0.2
            confidence = min(0.9, 0.45 + (0.1 * min(len(completed_durations), 4)))
            explanation = (
                f"ETA baseline basada en {len(completed_durations)} sesiones cerradas "
                f"de la mesa {table_id}."
            )
        else:
            baseline_duration = float(self.default_session_duration_seconds)
            spread = baseline_duration * 0.3
            confidence = 0.35
            explanation = "ETA baseline usando duracion por defecto mientras se construye historico real."

        elapsed_seconds = max(int((now - active_session.start_ts).total_seconds()), 0)
        remaining_seconds = max(baseline_duration - elapsed_seconds, 0.0)
        lower_bound = max(remaining_seconds - (spread / 2), 0.0)
        upper_bound = max(remaining_seconds + (spread / 2), lower_bound)

        return TablePrediction(
            prediction_id=f"pred_{uuid4().hex[:12]}",
            ts=now,
            table_id=table_id,
            model_name="baseline_mean_duration",
            prediction_type="eta_seconds",
            value=remaining_seconds,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence=confidence,
            explanation=explanation,
        )
