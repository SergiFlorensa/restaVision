from __future__ import annotations

from services.decision_engine.models import (
    OpportunityScore,
    QueueGroupSnapshot,
    TableSnapshot,
    TableState,
)


def score_table_opportunity(
    table: TableSnapshot,
    queue_group: QueueGroupSnapshot | None = None,
    cleaning_buffer_minutes: int = 3,
) -> OpportunityScore:
    score = 0
    reasons: list[str] = []
    compatible = True

    if queue_group is not None:
        compatible = table.capacity >= queue_group.party_size
        if compatible:
            score += 25
            reasons.append("mesa compatible")
            excess_capacity = table.capacity - queue_group.party_size
            score += max(0, 15 - excess_capacity * 5)
        else:
            score -= 40
            reasons.append("capacidad insuficiente")

    eta = _table_eta(table, cleaning_buffer_minutes)
    if table.state == TableState.READY:
        score += 45
        reasons.append("mesa lista")
    elif table.state == TableState.PENDING_CLEANING:
        score += 35
        reasons.append("solo falta limpieza")
    elif table.state == TableState.FINALIZING:
        score += 30
        reasons.append("mesa finalizando")
    elif table.state == TableState.BLOCKED:
        score += 20
        reasons.append("mesa bloqueada revisable")
    elif table.state == TableState.NEEDS_ATTENTION or table.needs_attention:
        score += 10
        reasons.append("requiere atencion")

    if eta is not None:
        if eta <= 5:
            score += 20
            reasons.append("ETA muy corta")
        elif eta <= 12:
            score += 12
            reasons.append("ETA razonable")
        elif eta > 25:
            score -= 15
            reasons.append("ETA alta")

    return OpportunityScore(
        table_id=table.table_id,
        score=max(0, min(100, score)),
        compatible=compatible,
        eta_minutes=eta,
        reason=tuple(reasons),
    )


def _table_eta(table: TableSnapshot, cleaning_buffer_minutes: int) -> float | None:
    if table.state == TableState.READY:
        return 0.0
    if table.state == TableState.PENDING_CLEANING:
        return float(cleaning_buffer_minutes)
    if table.eta_minutes is not None:
        return max(0.0, table.eta_minutes + cleaning_buffer_minutes)
    if table.state == TableState.FINALIZING:
        return float(8 + cleaning_buffer_minutes)
    return None
