# Feature Store, lineage y salud del modelo

## Propósito
Definir e implementar la base mínima para que RestaurIA no dependa de recalcular vídeo para responder al dashboard o a María.

Este documento aterriza tres piezas del sistema ML profesional:
- feature store local,
- registro de modelo,
- monitor de degradación silenciosa.

## Decisión
Para el MVP se usa SQLite local mediante `services/features/store.py`.

Motivos:
- no añade dependencias nuevas,
- funciona offline,
- tiene latencia suficiente para una cámara y una mesa,
- permite auditar eventos sin guardar vídeo completo,
- y puede migrarse después a PostgreSQL si el piloto crece.

## Esquema implementado

### `model_registry`
Guarda la versión técnica del modelo:
- `model_version`,
- `model_path`,
- `model_hash`,
- `input_width`,
- `input_height`,
- `runtime`,
- `quantization`,
- `normalization_json`,
- `registered_at`.

Uso:
- saber qué modelo produjo cada evento,
- evitar `training-serving skew`,
- comparar ONNX, OpenVINO, INT8 o FP32 con trazabilidad.

### `table_features`
Guarda el estado operativo actual por mesa:
- `table_id`,
- `current_state`,
- `last_event_timestamp`,
- `occupancy_duration_seconds`,
- `confidence_score`,
- `people_count`,
- `model_version`,
- `updated_at`.

Uso:
- dashboard rápido,
- consultas de María,
- recuperación tras reinicio,
- cálculo de KPIs sin reprocesar vídeo.

### `ai_lineage_events`
Guarda auditoría append-only de eventos de IA:
- `event_id`,
- `timestamp`,
- `camera_id`,
- `zone_id`,
- `table_id`,
- `event_type`,
- `model_version`,
- `confidence_score`,
- `image_path`,
- `latency_ms`,
- `payload_json`,
- `idempotency_key`.

Uso:
- auditar falsos positivos,
- vincular evento con frame exportado,
- evitar duplicados si el worker reintenta,
- medir latencia real por evento.

## Idempotencia
`idempotency_key` evita insertar el mismo evento dos veces.

Formato recomendado:

```text
{camera_id}:{frame_index}:{table_id}:{event_type}
```

Si el worker se reinicia o reintenta una operación, la base conserva un único evento lógico.

## Salud del modelo
`services/monitoring/health.py` implementa:
- media móvil de confianza,
- estado `warmup`, `ok`, `warning`, `critical`,
- comparación contra baseline,
- divergencia KL para drift de distribuciones.

Aplicación directa:
- si la confianza media cae bajo 0.40, revisar cámara, luz o calibración,
- si cae más de 0.15 respecto al baseline, generar aviso de recalibración,
- si la distribución de brillo cambia demasiado, marcar posible drift ambiental.

## Qué no se guarda
No se guardan:
- vídeos completos,
- imágenes dentro de SQL,
- rostros identificables como dato de negocio,
- pesos de modelos pesados.

Solo se guardan rutas, metadatos y features compactas.

## Flujo recomendado

```text
FramePacket
  -> detector
  -> ScoredDetection
  -> TableObservation
  -> FSM/eventos
  -> SQLiteFeatureStore
  -> dashboard / María / auditoría
```

## Integración en código
`FeatureStoreRecorder` conecta `RestaurantMVPService` con `SQLiteFeatureStore`:
- actualiza `table_features` tras cada observación,
- inserta eventos de lineage de forma idempotente,
- registra cambios manuales como `mark_table_ready`,
- conserva `model_version` en cada evento.

La integración es opcional para mantener los tests y demos en memoria, pero debe activarse en el worker local cuando se quiera auditoría persistente.

## Criterio de aceptación
La implementación es suficiente para Fase 1 si:
- registra versión de modelo,
- actualiza estado por mesa,
- guarda eventos de lineage de forma idempotente,
- permite consultar el estado sin abrir vídeo,
- detecta degradación de confianza con una ventana móvil.
