from __future__ import annotations

from uuid import uuid4

from services.decision_engine.models import (
    DecisionRecommendation,
    QueueGroupStatus,
    ServiceContext,
    TableState,
)
from services.decision_engine.pressure_index import calculate_pressure_index
from services.decision_engine.promise_engine import PromiseEngine
from services.decision_engine.table_opportunity_score import score_table_opportunity


class NextBestActionEngine:
    def __init__(self, promise_engine: PromiseEngine | None = None) -> None:
        self.promise_engine = promise_engine or PromiseEngine()

    def recommend(self, context: ServiceContext) -> DecisionRecommendation | None:
        recommendations = self.recommend_top(context, limit=1)
        return recommendations[0] if recommendations else None

    def recommend_top(
        self,
        context: ServiceContext,
        limit: int = 3,
    ) -> list[DecisionRecommendation]:
        pressure = calculate_pressure_index(context)
        recommendations: list[DecisionRecommendation] = []
        waiting_groups = [
            group for group in context.queue_groups if group.status == QueueGroupStatus.WAITING
        ]

        for group in waiting_groups:
            promise = self.promise_engine.recommend_wait(group, context.tables, context.now)
            if promise.risk in {"high", "breached"}:
                recommendations.append(
                    self._build(
                        mode=pressure.mode,
                        priority="P1",
                        answer=f"Actualizar espera del grupo {group.queue_group_id}",
                        confidence=promise.confidence,
                        impact="protect_guest_expectation",
                        queue_group_id=group.queue_group_id,
                        table_id=promise.candidate_table_id,
                        eta_minutes=promise.wait_max,
                        reason=("promesa en riesgo",) + promise.reason,
                    )
                )

            if promise.candidate_table_id is not None:
                recommendations.append(
                    self._build(
                        mode=pressure.mode,
                        priority="P1" if promise.wait_max <= 5 else "P2",
                        answer=(
                            f"Preparar {promise.candidate_table_id} "
                            f"para grupo de {group.party_size}"
                        ),
                        confidence=promise.confidence,
                        impact="reduce_wait_time",
                        table_id=promise.candidate_table_id,
                        queue_group_id=group.queue_group_id,
                        eta_minutes=promise.wait_max,
                        reason=promise.reason,
                    )
                )

        for table in context.tables:
            if table.state == TableState.PENDING_CLEANING and waiting_groups:
                recommendations.append(
                    self._build(
                        mode=pressure.mode,
                        priority="P1",
                        answer=f"Priorizar limpieza de {table.table_id}",
                        confidence=0.82,
                        impact="recover_table_capacity",
                        table_id=table.table_id,
                        eta_minutes=3,
                        reason=("mesa pendiente de limpieza", "cola activa"),
                    )
                )
            if table.state == TableState.NEEDS_ATTENTION or table.needs_attention:
                recommendations.append(
                    self._build(
                        mode=pressure.mode,
                        priority="P1",
                        answer=f"Revisar {table.table_id}",
                        confidence=0.74,
                        impact="protect_service_quality",
                        table_id=table.table_id,
                        reason=("posible atencion tardia",),
                    )
                )
            if table.state == TableState.FINALIZING and waiting_groups:
                best_group = max(
                    waiting_groups,
                    key=lambda group: score_table_opportunity(table, group).score,
                )
                opportunity = score_table_opportunity(table, best_group)
                recommendations.append(
                    self._build(
                        mode=pressure.mode,
                        priority="P2",
                        answer=(
                            f"Vigilar {table.table_id}: "
                            f"posible mesa para grupo {best_group.party_size}"
                        ),
                        confidence=0.68,
                        impact="anticipate_table_release",
                        table_id=table.table_id,
                        queue_group_id=best_group.queue_group_id,
                        eta_minutes=opportunity.eta_minutes,
                        reason=opportunity.reason,
                    )
                )

        ranked = sorted(
            recommendations,
            key=lambda recommendation: (
                _priority_rank(recommendation.priority),
                -(recommendation.confidence),
                recommendation.eta_minutes if recommendation.eta_minutes is not None else 999,
            ),
        )
        return ranked[:limit]

    @staticmethod
    def _build(
        *,
        mode: str,
        priority: str,
        answer: str,
        confidence: float,
        impact: str,
        table_id: str | None = None,
        queue_group_id: str | None = None,
        eta_minutes: float | None = None,
        reason: tuple[str, ...] = (),
    ) -> DecisionRecommendation:
        return DecisionRecommendation(
            decision_id=f"dec_{uuid4().hex[:12]}",
            mode=mode,
            priority=priority,
            question="Y ahora que hago?",
            answer=answer,
            table_id=table_id,
            queue_group_id=queue_group_id,
            eta_minutes=eta_minutes,
            confidence=round(confidence, 3),
            impact=impact,
            reason=reason,
        )


def _priority_rank(priority: str) -> int:
    return {"P1": 0, "P2": 1, "P3": 2}.get(priority, 3)
