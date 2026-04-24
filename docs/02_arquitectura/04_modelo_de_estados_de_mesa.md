# Modelo de estados de mesa

## Propósito
Definir una máquina de estados simple, explicable y útil para el MVP. La meta no es representar todos los matices de una sala real, sino establecer una semántica operativa estable sobre la que construir eventos, sesiones, persistencia, dashboard y ETA.

## Estados definidos

### `ready`
Mesa disponible para ser asignada.
- sin sesión activa,
- sin personas detectadas,
- operativamente usable.

### `occupied`
Mesa ocupada con una sesión activa.
- al menos una persona detectada,
- sesión abierta,
- estado base durante la mayor parte del servicio.

### `finalizing`
Mesa todavía ocupada, pero con señales de cierre progresivo.
- sigue habiendo personas detectadas,
- la sesión sigue abierta,
- el conteo baja respecto al pico anterior,
- ya ha pasado un tiempo mínimo suficiente para considerar que podría estar terminando.

### `payment`
Estado reservado para evolución posterior.
- no es obligatorio en el MVP automático actual,
- queda previsto para señales futuras de pago manual o semiautomático.

### `pending_cleaning`
La sesión ha terminado, pero la mesa todavía no debe considerarse lista.
- no hay personas detectadas,
- la sesión ya se ha cerrado,
- falta confirmación de limpieza o reseteo operativo.

## Estados fuera de esta primera implementación
- `waiting`
- `eating`
- `served`

Esos estados podrán aparecer más adelante cuando exista más señal operativa, integración con POS o reglas de negocio mejor definidas.

## Reglas de transición del MVP

### `ready -> occupied`
Se produce cuando:
- una observación detecta `people_count > 0`,
- no existe sesión activa.

Acciones:
- crear sesión,
- emitir `table_occupied`,
- emitir `session_started`.

### `occupied -> finalizing`
Se produce cuando:
- la sesión sigue activa,
- el conteo de personas baja respecto a la observación anterior,
- ha pasado un mínimo temporal razonable desde el inicio de sesión.

Objetivo:
- dar una señal temprana al dashboard sin cerrar todavía la sesión.

### `occupied -> pending_cleaning`
Se produce cuando:
- el conteo llega a `0`,
- la mesa tenía una sesión activa.

Acciones:
- cerrar sesión,
- calcular duración,
- emitir `table_released`,
- emitir `session_ended`,
- emitir `table_pending_cleaning`.

### `finalizing -> occupied`
Se produce cuando:
- la mesa recupera ocupación estable,
- aumenta o se recupera el conteo de personas.

Objetivo:
- evitar que un descenso puntual fuerce una lectura incorrecta de cierre.

### `finalizing -> pending_cleaning`
Se produce cuando:
- la sesión activa termina con `people_count = 0`.

### `pending_cleaning -> ready`
Se produce cuando:
- existe confirmación manual de que la mesa vuelve a estar operativamente disponible.

En el MVP actual esta transición se modela mediante endpoint manual.

## Principios de diseño
- El sistema distingue entre “sesión terminada” y “mesa disponible”.
- Una mesa vacía no pasa automáticamente a `ready`; primero pasa por `pending_cleaning`.
- `finalizing` es una ayuda operativa, no una verdad absoluta.
- Toda transición relevante debe dejar rastro mediante eventos.

## Opción de rechazo
La FSM no debe cambiar de estado con observaciones poco fiables.

Si una observación llega por debajo de `min_transition_confidence`:
- se registra `people_counted`,
- se registra `low_confidence_observation`,
- no se crea ni se cierra sesión,
- no se modifica el estado operativo de la mesa.

Esto aplica de forma práctica la separación entre inferencia y decisión: la cámara puede ver una señal dudosa, pero el software no tiene por qué actuar sobre ella.

## Traducción a producto
Esta máquina de estados permite responder ya a preguntas útiles:
- si una mesa está realmente disponible,
- cuánto lleva ocupada,
- si parece estar entrando en fase de cierre,
- cuándo terminó la sesión anterior,
- y si todavía queda una acción operativa pendiente antes de reasignarla.
