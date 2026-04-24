# Pipeline ligero para cámara única

## Propósito
Definir una ruta de implementación realista para ejecutar RestaurIA en un ordenador normal conectado a una cámara.

El objetivo no es usar los modelos más avanzados, sino conseguir un resultado estable, útil y defendible a nivel de portfolio:
- detección suficientemente fiable,
- conteo por mesa,
- latencia baja,
- consumo razonable de CPU/RAM,
- y arquitectura preparada para mejorar después.

## Decisión principal
Para una primera versión con hardware normal:
- no usar GRU en producción,
- no usar BERT ni agente conversacional completo,
- no usar aprendizaje por refuerzo,
- no entrenar detectores desde cero,
- no procesar todo el frame a máxima resolución si no hace falta.

La primera versión debe usar:
- una cámara,
- zonas configuradas,
- detecciones ligeras,
- NMS,
- asignación espacial,
- suavizado temporal,
- FSM de mesa,
- ETA baseline.
- y orquestación puntual para análisis pesado de María.

## Flujo recomendado

```text
cámara / vídeo
  -> frame
  -> detector ligero de personas
  -> NMS
  -> suavizado Kalman opcional
  -> asignación a zona/mesa
  -> metricas proxemicas opcionales si hay coordenadas en metros
  -> conteo raw
  -> suavizado temporal
  -> TableObservation
  -> FSM
  -> eventos / sesión / ETA
  -> trigger selectivo de Maria (si aplica)
  -> dashboard
```

## Bloque implementado
Ya existe una primera pieza independiente del detector:
- `services/vision/geometry.py`
- `services/vision/observation_adapter.py`
- `services/vision/kalman.py`
- `services/proxemics/engine.py`
- `services/maria/orchestrator.py`

Esto permite probar la lógica central sin cámara real:
- recibe detecciones con bounding boxes,
- limpia duplicados con NMS,
- suaviza bounding boxes con Kalman cuando se use tracking,
- asigna personas a zonas,
- calcula senales proxemicas si existe calibracion a metros,
- cuenta personas por mesa,
- suaviza pérdidas breves de detección,
- genera `TableObservation`.
- decide cuándo lanzar análisis pesado de forma puntual.

## Por qué esto es mejor que empezar con GRU
Una GRU puede ser útil cuando existan muchos datos históricos, pero ahora sería prematura:
- no hay dataset suficiente,
- no hay secuencias reales de restaurante,
- no hay etiquetas fiables de fases de servicio,
- y el coste de entrenar/validar puede distraer del MVP.

El suavizado temporal resuelve ya un problema real:
- si la cámara pierde una persona durante un frame,
- no se debe cerrar la sesión automáticamente.

Esto aporta estabilidad inmediata con coste mínimo.

### Opción de rechazo
La FSM rechaza transiciones de baja confianza mediante `low_confidence_observation`.

Objetivo:
- no abrir sesiones por detecciones dudosas,
- no cerrar sesiones por un frame vacío de baja confianza,
- pedir más evidencia antes de actuar.

## Configuración inicial recomendada

### Cámara
- 1080p como captura máxima si el equipo lo soporta,
- procesado interno a 640px o 720px de ancho si la latencia sube,
- cámara fija,
- encuadre estable,
- iluminación lo más constante posible.

### FPS
- objetivo inicial: 5-10 FPS procesados,
- no hace falta 30 FPS para saber si una mesa está ocupada,
- el ETA no debe recalcularse por frame.

### Detección
Primera opción:
- detector de personas preentrenado,
- sin fine-tuning inicial,
- umbral de confianza conservador.

Después:
- evaluar YOLO/ONNX/SSD ligero según rendimiento real,
- medir antes de cambiar modelo.

### NMS
Umbral inicial:
- `0.45` a `0.50`.

Objetivo:
- evitar contar dos veces a la misma persona.

### Asignación espacial
Estrategia inicial:
- punto inferior central dentro de la zona,
- fallback por IoU si hay geometrías rectangulares claras.

Motivo:
- en personas sentadas, el IoU puede ser bajo aunque la persona pertenezca a la mesa.

### Suavizado temporal
Configuración inicial:
- confirmar ocupación con 2 observaciones positivas,
- confirmar vacío con 3 observaciones vacías,
- ventana de 4-5 observaciones.

Motivo:
- evitar cambios falsos por oclusión, desenfoque o fallo puntual del detector.

## Qué medir desde el principio
- FPS efectivo,
- latencia por frame,
- falsos cambios de estado,
- falsos vacíos,
- falsos ocupados,
- uso de CPU,
- uso de RAM,
- estabilidad tras 30-60 minutos.

## Qué posponer

### GRU
Posponer hasta tener:
- cientos de sesiones,
- eventos de fase fiables,
- datos de cierre reales,
- baseline clásico medido.

### BERT / agente de voz
Posponer hasta tener:
- dashboard operativo,
- alertas simples,
- vocabulario real de uso,
- necesidad demostrada de manos libres.

### Aprendizaje por refuerzo
Posponer mucho más:
- primero reglas,
- después simulador,
- después evaluación offline,
- nunca decisiones automáticas sin supervisión humana.

### Detección de datáfono, billetes o platos
Posponer hasta tener:
- dataset propio,
- revisión legal/ética,
- métricas de falsos positivos,
- utilidad clara sobre ETA o limpieza.

## Criterio profesional
Un buen resultado de portfolio no exige demostrar todo.

Exige demostrar que:
- la arquitectura está bien separada,
- el sistema funciona con una cámara real,
- los estados son estables,
- los eventos se persisten,
- el dashboard ayuda a decidir,
- y las decisiones técnicas están justificadas por medición.

## Siguiente implementación
Integrar `DetectionToObservationAdapter` con una fuente real:
1. capturar frame con OpenCV,
2. ejecutar detector ligero,
3. convertir detecciones a `ScoredDetection`,
4. generar `TableObservation`,
5. enviarlas al `RestaurantMVPService`.
