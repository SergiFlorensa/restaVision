# IoU, NMS y asignación espacial

## Propósito
Definir cómo se aplican IoU, punto inferior central y NMS en RestaurIA para convertir detecciones visuales en observaciones útiles por mesa o zona.

Este documento prepara el puente entre:
- detector visual,
- geometría de zonas,
- conteo por mesa,
- y generación de eventos `people_counted`.

## Decisión técnica
RestaurIA no debe asumir que una detección pertenece a una mesa solo porque aparece cerca en la imagen.

Debe existir una regla geométrica explícita y testeable:
- solape entre bounding boxes,
- punto inferior central dentro de zona,
- o una combinación de ambas cuando haya perspectiva corregida.

## Conceptos

### Bounding box
Rectángulo que delimita una detección o zona:
- `x_min`,
- `y_min`,
- `x_max`,
- `y_max`.

### IoU
Intersection over Union mide cuánto se solapan dos cajas.

Uso:
- validar si una detección cae dentro de la zona de una mesa,
- seleccionar la mejor zona cuando una detección toca varias,
- eliminar duplicados con NMS.

Limitación:
- si la zona de mesa es grande y la persona ocupa solo una parte pequeña, el IoU puede ser bajo aunque la asignación sea correcta.

### Punto inferior central
Para personas, suele ser más útil mirar el punto inferior central de la caja:
- aproxima la posición de los pies o base de la persona,
- ayuda a decidir en qué zona está situada,
- evita penalizar detecciones altas o estrechas.

Aplicación:
- usarlo especialmente con vista cenital o zonas de suelo.

### NMS
Non-Maximum Suppression elimina detecciones duplicadas:
- ordena por confianza,
- conserva la detección de mayor score,
- elimina cajas del mismo tipo que solapan demasiado.

Uso:
- evitar contar dos veces a la misma persona,
- limpiar el dashboard,
- estabilizar eventos.

## Implementación actual
Se añade:
- `services/vision/geometry.py`
- `services/vision/observation_adapter.py`

Contiene:
- `BoundingBox`,
- `bbox_from_polygon`,
- `assign_detections_to_zones_by_iou`,
- `assign_detections_to_zones_by_bottom_center`,
- `non_max_suppression`.
- `DetectionToObservationAdapter`,
- `TemporalCountSmoother`.
- `BoundingBoxKalmanSmoother`.

El suavizado Kalman vive en `services/vision/kalman.py` y queda preparado para estabilizar el centro de las cajas cuando exista detector real.

## Umbrales iniciales
No hay un umbral universal.

Recomendación inicial:
- NMS personas: `0.45` a `0.50`,
- IoU persona-zona: calibrar con datos reales,
- bottom-center: usar como fallback o regla principal cuando las zonas representen suelo.

## Cómo encaja con el adaptador de vídeo
Flujo futuro:

```text
frame
  -> detector de personas
  -> NMS
  -> suavizado Kalman opcional
  -> detecciones limpias
  -> asignación detección-zona
  -> conteo por mesa
  -> TableObservation
  -> FSM / eventos
```

La primera versión de este adaptador ya acepta detecciones estructuradas y produce `TableObservation`.
Todavía falta conectar una fuente real de frames y un detector real de personas.

## Criterio de aceptación
La asignación espacial estará lista para integrarse en el adaptador cuando:
- las funciones estén cubiertas por tests,
- se pueda asignar una detección a la mesa correcta,
- se eviten duplicados con NMS,
- y los umbrales estén documentados por escenario de prueba.

## Riesgos
- umbrales mal calibrados,
- cámaras con perspectiva fuerte,
- mesas muy juntas,
- camareros cruzando zonas,
- detecciones parciales por oclusión.

## Mitigaciones
- homografía o vista cenital cuando sea viable,
- zonas poligonales y no solo rectangulares en fases posteriores,
- suavizado temporal de conteo,
- confirmación por varias observaciones antes de cambiar estado.
