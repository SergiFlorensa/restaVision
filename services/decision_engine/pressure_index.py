from __future__ import annotations

from services.decision_engine.models import PressureIndex, ServiceContext, TableState


def calculate_pressure_index(context: ServiceContext) -> PressureIndex:
    table_count = len(context.tables)
    occupied_count = sum(1 for table in context.tables if table.state != TableState.READY)
    queue_count = sum(1 for group in context.queue_groups if group.status == "waiting")
    finalizing_count = sum(1 for table in context.tables if table.state == TableState.FINALIZING)
    cleaning_count = sum(
        1 for table in context.tables if table.state == TableState.PENDING_CLEANING
    )
    attention_count = sum(
        1
        for table in context.tables
        if table.needs_attention or table.state == TableState.NEEDS_ATTENTION
    )

    occupancy_pressure = (occupied_count / table_count * 45.0) if table_count else 0.0
    queue_pressure = min(queue_count * 12.0, 30.0)
    alert_pressure = min(context.p1_alert_count * 8.0, 20.0)
    service_pressure = min((finalizing_count + cleaning_count + attention_count) * 5.0, 20.0)
    staff_pressure = 10.0 if context.staff_shortage else 0.0

    raw_value = (
        occupancy_pressure + queue_pressure + alert_pressure + service_pressure + staff_pressure
    )
    value = max(0, min(100, round(raw_value)))

    reasons: list[str] = []
    if table_count and occupied_count / table_count >= 0.85:
        reasons.append("ocupacion alta")
    if queue_count:
        reasons.append("cola activa")
    if context.p1_alert_count:
        reasons.append("alertas P1 activas")
    if finalizing_count or cleaning_count:
        reasons.append("mesas en transicion")
    if attention_count:
        reasons.append("mesas requieren atencion")
    if context.staff_shortage:
        reasons.append("falta de personal")

    if value >= 75:
        mode = "critical_service"
    elif value >= 45:
        mode = "busy"
    else:
        mode = "normal"

    return PressureIndex(value=value, mode=mode, reason=tuple(reasons))
