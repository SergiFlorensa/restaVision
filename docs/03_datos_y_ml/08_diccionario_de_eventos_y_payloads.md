# Diccionario de eventos y payloads del MVP

## Proposito
Definir que eventos existen en el MVP, cuando se emiten y que payload minimo deben incluir. Sin este diccionario, la trazabilidad y la futura analitica quedan mal fundamentadas.

## Convenciones
- todos los eventos llevan `event_id`, `ts`, `camera_id`, `zone_id`, `table_id`, `confidence`,
- si aplica, tambien llevan `session_id` y `queue_group_id`,
- el `payload_json` contiene solo datos especificos del evento,
- el nombre tecnico del evento se mantiene en ingles en codigo y API,
- la explicacion funcional se documenta en espanol.

## Eventos de observacion y mesa

### `people_counted`
Se emite en cada observacion procesada.

Payload minimo:
- `people_count`
- `previous_people_count`
- `table_capacity`

### `table_occupied`
Se emite cuando una mesa pasa de disponible a ocupada.

Payload minimo:
- `people_count`

### `session_started`
Se emite cuando se crea una nueva sesion de mesa.

Payload minimo:
- `session_id`

### `table_state_changed`
Se emite en cada cambio de estado de la maquina de estados.

Payload minimo:
- `from_state`
- `to_state`
- `reason`

### `table_finalizing_detected`
Se emite cuando una mesa muestra senales de posible finalizacion.

Payload minimo:
- `session_id`
- `signals`
- `eta_minutes`

### `table_blocked_detected`
Se emite cuando una mesa sigue ocupada pero parece haber dejado de generar valor operativo.

Payload minimo:
- `session_id`
- `duration_seconds`
- `baseline_seconds`
- `signals`

### `table_needs_attention`
Se emite cuando una mesa podria necesitar atencion inicial o seguimiento.

Payload minimo:
- `session_id`
- `attention_reason`
- `elapsed_seconds`

### `table_released`
Se emite cuando la ocupacion termina y la mesa deja de tener personas detectadas.

Payload minimo:
- `session_id`

### `session_ended`
Se emite cuando se cierra la sesion.

Payload minimo:
- `session_id`
- `duration_seconds`

### `table_pending_cleaning`
Se emite cuando la mesa queda vacia, pero aun no disponible.

Payload minimo:
- `table_id`
- `session_id`

### `table_ready`
Se emite cuando la mesa vuelve a estar lista para asignacion.

Payload minimo:
- `table_id`

## Eventos de cola y promesa

### `queue_group_arrived`
Se emite cuando se registra un grupo en cola.

Payload minimo:
- `queue_group_id`
- `party_size`
- `arrival_ts`

### `wait_promise_created`
Se emite cuando se comunica una espera recomendada.

Payload minimo:
- `queue_group_id`
- `promised_wait_min`
- `promised_wait_max`
- `candidate_table_id`

### `wait_promise_at_risk`
Se emite cuando una promesa puede incumplirse.

Payload minimo:
- `queue_group_id`
- `elapsed_minutes`
- `promised_wait_max`
- `reason`

### `queue_group_seated`
Se emite cuando un grupo en cola se sienta.

Payload minimo:
- `queue_group_id`
- `table_id`
- `actual_wait_minutes`

### `queue_group_abandoned`
Se emite cuando un grupo se va antes de sentarse.

Payload minimo:
- `queue_group_id`
- `elapsed_minutes`
- `last_promised_wait_max`

## Eventos de decision

### `recommendation_generated`
Se emite cuando el motor crea una recomendacion.

Payload minimo:
- `decision_id`
- `priority`
- `answer`
- `table_id`
- `queue_group_id`
- `eta_minutes`
- `reason`
- `expires_in_seconds`

### `recommendation_accepted`
Se emite cuando el encargado acepta o ejecuta una recomendacion.

Payload minimo:
- `decision_id`
- `accepted_by`

### `recommendation_ignored`
Se emite cuando una recomendacion se descarta o caduca.

Payload minimo:
- `decision_id`
- `reason`

### `recommendation_feedback_recorded`
Se emite cuando se registra si la recomendacion fue util.

Payload minimo:
- `decision_id`
- `useful`
- `outcome`

## Eventos de presion operativa

### `pressure_index_updated`
Se emite periodicamente o ante cambios relevantes.

Payload minimo:
- `pressure_index`
- `mode`
- `occupied_tables`
- `waiting_groups`
- `p1_alerts`

### `critical_service_mode_enabled`
Se emite cuando el sistema recomienda o activa modo critico.

Payload minimo:
- `pressure_index`
- `reason`

## Eventos previstos para siguientes iteraciones
- `staff_zone_undercovered`
- `kitchen_delay_detected`
- `reservation_conflict_detected`
- `manual_override_applied`

## Relacion con base de datos
Estos eventos se persistiran en la tabla `events`, mientras que las sesiones agregadas viviran en `sessions`, los grupos en `queue_groups` y las recomendaciones en `decision_recommendations`.

La clave es que cada accion recomendada pueda reconstruirse a partir de observaciones, eventos, sesiones, cola y feedback.
