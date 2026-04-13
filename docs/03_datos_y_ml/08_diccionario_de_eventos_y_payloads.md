# Diccionario de eventos y payloads del MVP

## Propósito
Definir qué eventos existen en el MVP, cuándo se emiten y qué payload mínimo deben incluir. Sin este diccionario, la trazabilidad y la futura analítica quedan mal fundamentadas.

## Convenciones
- todos los eventos llevan `event_id`, `ts`, `camera_id`, `zone_id`, `table_id`, `confidence`,
- el `payload_json` contiene solo datos específicos del evento,
- el nombre técnico del evento se mantiene en inglés en código y API,
- la explicación funcional se documenta en español.

## Eventos activos en la implementación inicial

### `people_counted`
Se emite en cada observación procesada.

Payload mínimo:
- `people_count`
- `previous_people_count`
- `table_capacity`

Uso:
- trazabilidad básica,
- depuración del pipeline,
- base para reglas de estado.

### `entry_to_table`
Se emite cuando el conteo sube respecto a la observación anterior y la mesa ya estaba ocupada.

Payload mínimo:
- `delta`

Uso:
- detectar incorporación de personas,
- revisar estabilidad del conteo.

### `exit_from_table`
Se emite cuando el conteo baja, pero la mesa sigue ocupada.

Payload mínimo:
- `delta`

Uso:
- detectar salidas parciales,
- activar posible transición a `finalizing`.

### `table_occupied`
Se emite cuando una mesa pasa de disponible a ocupada.

Payload mínimo:
- `people_count`

Uso:
- inicio operativo de una ocupación real.

### `session_started`
Se emite cuando se crea una nueva sesión de mesa.

Payload mínimo:
- `session_id`

Uso:
- enlazar eventos posteriores con una sesión concreta.

### `table_released`
Se emite cuando la ocupación termina y la mesa deja de tener personas detectadas.

Payload mínimo:
- `session_id`

Uso:
- marca el fin visual de la ocupación.

### `session_ended`
Se emite cuando se cierra la sesión.

Payload mínimo:
- `session_id`
- `duration_seconds`

Uso:
- persistencia histórica,
- cálculo de ETA baseline,
- análisis posterior.

### `table_pending_cleaning`
Se emite cuando la mesa queda vacía, pero aún no disponible.

Payload mínimo:
- `table_id`

Uso:
- separar liberación visual de disponibilidad real.

### `table_ready`
Se emite cuando la mesa vuelve a estar lista para asignación.

Payload mínimo:
- `table_id`

Uso:
- cierre del ciclo operativo completo de la mesa.

### `table_state_changed`
Se emite en cada cambio de estado de la máquina de estados.

Payload mínimo:
- `from_state`
- `to_state`

Uso:
- auditoría funcional,
- reconstrucción temporal,
- explicación de decisiones en dashboard.

## Eventos previstos para siguientes iteraciones
- `payment_started`
- `manual_override_applied`
- `recommendation_generated`
- `alert_emitted`
- `anomaly_flagged`

## Relación con base de datos
Estos eventos se persistirán en la tabla `events`, mientras que las sesiones agregadas vivirán en `sessions`. La clave es que el estado actual debe poder reconstruirse a partir de observaciones, eventos y sesiones sin depender de lógica oculta.

