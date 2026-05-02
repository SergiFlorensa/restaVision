# Esquema de datos

## Objetivo
La base de datos debe conservar memoria operativa: mesas, sesiones, eventos, cola, predicciones, recomendaciones y feedback.

No debe guardar video continuo, caras, audio conversacional ni datos personales innecesarios.

## Tabla `cameras`
- camera_id
- name
- status

## Tabla `zones`
- zone_id
- name
- camera_id
- polygon_definition
- zone_type
- roi_bbox
- active

## Tabla `tables`
- table_id
- name
- capacity
- zone_id
- active

## Tabla `table_runtime`
- table_id
- state
- last_people_count
- people_count_peak
- active_session_id
- updated_at
- phase
- needs_attention
- assigned_staff
- last_attention_at
- operational_note

## Tabla `operational_actions`
- action_id
- ts
- action_type
- table_id
- queue_group_id
- assigned_staff
- target_channel
- message
- payload_json

## Tabla `sessions`
- session_id
- table_id
- start_ts
- end_ts
- people_count_initial
- people_count_peak
- final_status
- duration_seconds

## Tabla `queue_groups`
- queue_group_id
- arrival_ts
- party_size
- status
- promised_wait_min
- promised_wait_max
- promised_at
- preferred_zone_id
- assigned_table_id
- seated_at
- abandoned_at
- notes

## Tabla `events`
- event_id
- ts
- camera_id
- zone_id
- table_id (nullable)
- session_id (nullable)
- queue_group_id (nullable)
- event_type
- confidence
- payload_json

## Tabla `predictions`
- prediction_id
- ts
- table_id
- model_name
- prediction_type
- value
- lower_bound
- upper_bound
- confidence
- explanation

## Tabla `alerts`
- alert_id
- ts
- table_id
- session_id
- queue_group_id
- alert_type
- severity
- message
- score
- evidence_json
- acknowledged_by

## Tabla `decision_recommendations`
- decision_id
- ts
- mode
- priority
- question
- answer
- table_id
- session_id
- queue_group_id
- eta_minutes
- confidence
- impact
- reason_json
- expires_at
- status

## Tabla `decision_feedback`
- feedback_id
- decision_id
- ts
- feedback_type
- accepted
- useful
- outcome_json
- comment

## Tabla `service_snapshots`
- snapshot_id
- ts
- pressure_index
- mode
- occupied_tables
- waiting_groups
- p1_alerts
- payload_json

## Tabla `model_versions`
- model_version_id
- module
- version
- trained_at
- dataset_ref
- metrics_json

## Estado de implementacion
La primera capa ORM ya cubre:
- `cameras`,
- `zones` con `polygon_definition`,
- `tables`,
- `table_runtime`,
- `sessions`,
- `events`,
- `predictions`.
- `queue_groups`,
- `decision_recommendations`,
- `decision_feedback`,
- `operational_actions`.

Quedan como tablas prioritarias de la nueva configuracion:
- `alerts` persistidas,
- `service_snapshots`.

## Criterio de diseno
Cada recomendacion debe poder reconstruirse con:
- estado de mesa,
- sesion,
- grupo en cola,
- eventos recientes,
- prediccion o ETA,
- regla aplicada,
- feedback posterior.
