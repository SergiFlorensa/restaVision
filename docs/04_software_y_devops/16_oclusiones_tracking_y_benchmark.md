# Oclusiones, tracking ligero y benchmarking

## Propósito
Definir las piezas de robustez necesarias para que RestaurIA no cierre sesiones por errores visuales transitorios.

El objetivo es gestionar tres problemas reales de cámara:
- oclusión temporal de una mesa,
- pérdida breve de detecciones YOLO,
- latencia variable por CPU o memoria.

## Oclusiones
`services/events/occlusion.py` implementa `OcclusionManager`.

Funciona antes de la máquina de estados:
1. recibe la observación cruda,
2. consulta el runtime actual de la mesa,
3. decide si la mesa sigue ocupada por histéresis,
4. entrega una observación efectiva a la FSM,
5. emite eventos `occlusion_suspected` o `camera_blocked`.

Reglas iniciales:
- no cerrar mesa por un único frame vacío,
- no cerrar mesa con confianza baja,
- no cerrar si el paso de ocupada a vacía es físicamente demasiado brusco,
- alertar si hay varias observaciones con confianza casi nula.

## Tracking LK
`services/vision/lk_tracker.py` implementa `LKTracker` con Lucas-Kanade piramidal.

Uso previsto:
- YOLO inicializa cajas de persona cada N frames,
- LK sigue puntos Shi-Tomasi dentro de cada caja,
- el sistema usa centroides intermedios para mantener continuidad visual,
- YOLO reancla periódicamente para corregir deriva.

Esto reduce CPU porque no obliga a ejecutar YOLO en cada frame.

`services/vision/hybrid_inference.py` integra el ciclo híbrido:
- detector caro cada N frames,
- tracking LK en los frames intermedios,
- reanclaje automático si se pierden puntos,
- conversión robusta de puntos LK a `ScoredDetection`.

La conversión punto→caja usa filtrado estadístico por `k_sigma` para evitar que un punto errante estire artificialmente la caja.

## Analítica temporal
`services/events/analytics.py` resume sesiones cerradas ya persistidas:
- duración total por mesa,
- duración media,
- mínimo y máximo,
- número de sesiones cerradas.

La regla de diseño se mantiene: no escribir cada frame en base de datos; registrar sesiones y eventos de transición.

## Calibración geométrica
`services/vision/calibration.py` implementa:
- cálculo de homografía por mesa,
- normalización de puntos 0-1,
- extracción de ROI por slicing de NumPy,
- guardado/carga de calibraciones en JSON,
- rectificación de mesa con `warpPerspective` cuando OpenCV está instalado.

`infra/scripts/calibrate_tables.py` permite marcar 4 esquinas por mesa con ratón:

```powershell
python infra/scripts/calibrate_tables.py --source 0 --table table_01 --output data/processed/table_calibrations.json
```

Para varias mesas:

```powershell
python infra/scripts/calibrate_tables.py --source 0 --table table_01 --table table_02
```

Regla de rendimiento:
- usar slicing para extraer la mesa,
- rectificar solo el ROI necesario,
- no aplicar homografía al frame completo.

## Visión clásica ligera
`services/vision/classical.py` implementa un carril rápido sin deep learning:
- conversión BGR/gris,
- ecualización de histograma,
- blur gaussiano,
- gradientes Sobel,
- señal compacta por mesa (`edge_density`, `mean_gradient`, `object_candidate`).

Uso previsto:
- detectar actividad visual estática en la mesa,
- apoyar detección de platos/cubiertos sin ejecutar YOLO,
- decidir si una ROI merece análisis pesado,
- mejorar robustez en mesas oscuras.

Regla de adopción:
- Sobel/gradientes sirven como señal auxiliar, no como verdad semántica.
- YOLO u otro detector semántico sigue siendo la fuente de verdad para personas.

## Benchmark P99
Para el TFG debe medirse:
- P50,
- P95,
- P99,
- jitter,
- warm-up descartado,
- latencia por etapa.

La métrica importante no es solo el promedio. Si P99 es alto, María puede parecer congelada aunque el promedio sea bueno.

`services/monitoring/latency.py` implementa:
- `LatencyTracker` con descarte de warm-up,
- `LatencySummary` con P50/P95/P99 y jitter,
- exportación CSV para anexos del TFG,
- contexto `measure()` basado en `time.perf_counter()`.

## Criterio de aceptación
La integración es válida si:
- una oclusión breve no cierra la sesión,
- una cámara bloqueada genera alerta técnica,
- el tracking devuelve centroides entre detecciones,
- la latencia se mide por percentiles antes de optimizar más.
