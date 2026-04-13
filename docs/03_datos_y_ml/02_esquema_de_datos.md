# Esquema de datos

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

## Tabla `alerts`
- alert_id
- ts
- table_id
- severity
- alert_type
- explanation
- acknowledged_by

## Tabla `model_versions`
- model_version_id
- module
- version
- trained_at
- dataset_ref
- metrics_json
