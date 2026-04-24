# Esquema de datos

## Tabla `cameras`
- camera_id
- name
- status

## Tabla `tables`
- table_id
- name
- capacity
- zone_id
- active

## Tabla `zones`
- zone_id
- name
- camera_id
- polygon_definition
- zone_type
- roi_bbox
- active

## Tabla `table_runtime`
- table_id
- state
- last_people_count
- people_count_peak
- active_session_id
- updated_at

## Tabla `sessions`
- session_id
- table_id
- start_ts
- end_ts
- people_count_initial
- people_count_peak
- final_status
- duration_seconds

## Tabla `events`
- event_id
- ts
- camera_id
- zone_id
- table_id (nullable)
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

## Estado de implementación
La primera capa ORM ya cubre:
- `cameras`,
- `zones` con `polygon_definition`,
- `tables`,
- `table_runtime`,
- `sessions`,
- `events`,
- `predictions`.

Quedan como tablas de fases posteriores:
- `alerts` si se necesita auditoria persistente de alertas,
- `model_versions`.

Quedan como ampliaciones de columnas:
- `zone_type`,
- `roi_bbox`,
- `active` en zonas si se necesita desactivar una zona sin borrarla.

## Tabla `alerts`
- alert_id
- ts
- table_id
- session_id
- alert_type
- severity
- message
- score
- evidence_json
- acknowledged_by

Estado:
- la primera version de alertas funciona en memoria desde `services/alerts/anomaly.py`,
- se expone por `GET /api/v1/alerts`,
- la persistencia queda aplazada hasta que el dashboard necesite historico auditable.

## Tabla `model_versions`
- model_version_id
- module
- version
- trained_at
- dataset_ref
- metrics_json
