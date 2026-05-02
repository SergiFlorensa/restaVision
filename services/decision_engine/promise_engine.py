from __future__ import annotations

from datetime import datetime
from math import ceil

from services.decision_engine.models import (
    PromiseRecommendation,
    QueueGroupSnapshot,
    TableSnapshot,
)
from services.decision_engine.table_opportunity_score import score_table_opportunity


class PromiseEngine:
    def __init__(self, wait_padding_minutes: int = 2) -> None:
        self.wait_padding_minutes = wait_padding_minutes

    def recommend_wait(
        self,
        queue_group: QueueGroupSnapshot,
        tables: tuple[TableSnapshot, ...],
        now: datetime,
    ) -> PromiseRecommendation:
        scored_tables = [score_table_opportunity(table, queue_group) for table in tables]
        candidates = [candidate for candidate in scored_tables if candidate.compatible]
        candidates_with_eta = [
            candidate for candidate in candidates if candidate.eta_minutes is not None
        ]

        if not candidates_with_eta:
            return PromiseRecommendation(
                queue_group_id=queue_group.queue_group_id,
                candidate_table_id=None,
                wait_min=20,
                wait_max=30,
                confidence=0.35,
                risk="unknown",
                message="No hay mesa candidata clara; dar espera conservadora.",
                reason=("sin mesa compatible con ETA",),
            )

        best = min(
            candidates_with_eta,
            key=lambda candidate: (candidate.eta_minutes, -candidate.score),
        )
        wait_min = max(0, ceil(best.eta_minutes))
        wait_max = wait_min + self.wait_padding_minutes
        risk = self._promise_risk(queue_group, now)
        confidence = min(0.95, 0.45 + best.score / 200)

        return PromiseRecommendation(
            queue_group_id=queue_group.queue_group_id,
            candidate_table_id=best.table_id,
            wait_min=wait_min,
            wait_max=wait_max,
            confidence=round(confidence, 3),
            risk=risk,
            message=f"Ofrecer espera de {wait_min}-{wait_max} min.",
            reason=best.reason,
        )

    @staticmethod
    def _promise_risk(queue_group: QueueGroupSnapshot, now: datetime) -> str:
        if queue_group.promised_wait_max is None or queue_group.promised_at is None:
            return "not_promised"

        elapsed_minutes = (now - queue_group.promised_at).total_seconds() / 60
        if elapsed_minutes >= queue_group.promised_wait_max:
            return "breached"
        if elapsed_minutes >= queue_group.promised_wait_max * 0.8:
            return "high"
        return "low"
