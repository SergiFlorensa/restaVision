# Adaptador YOLO para detección de personas y objetos de restaurante

## Decisión

Añadir un adaptador opcional para Ultralytics YOLO que traduzca detecciones del modelo a `ScoredDetection`, el contrato interno de RestaurIA.

La decisión se basa en el bloque de Computer Vision de *Dive into Deep Learning*:

- detección de objetos y bounding boxes,
- anchor boxes,
- predicción de cajas,
- non-maximum suppression,
- detección multiescala,
- fine-tuning de modelos preentrenados.

## Encaje en RestaurIA

El adaptador vive en `services/vision/yolo_detector.py` y no sustituye el detector demo OpenCV. Son capas separadas:

- `person_demo.py`: prueba rápida sin pesos YOLO.
- `yolo_detector.py`: detección real con Ultralytics YOLO, filtrada por modo (`person` o clases COCO de restaurante).
- `hybrid_inference.py`: carril futuro para combinar YOLO periódico y tracking LK.
- `observation_adapter.py`: conversión futura de detecciones a observaciones de mesa.

## Qué aporta al MVP

- Permite probar una mesa real en casa con webcam.
- Filtra por clase `person` para evitar ruido de COCO.
- Añade un modo exploratorio de restaurante para probar `person`, `chair`, `dining table`, `cup`, `bottle`, `wine glass`, `bowl`, `fork`, `knife`, `spoon` y `pizza`.
- Usa umbral de confianza configurable.
- Usa IoU/NMS para evitar duplicados.
- Recorta cajas al tamaño del frame y descarta cajas demasiado pequeñas.
- Mantiene Ultralytics como dependencia opcional de ejecución: el backend arranca aunque YOLO no esté instalado.

## Endpoints de demo

```text
GET /api/v1/demo/yolo-person/status
GET /api/v1/demo/yolo-person/stream
GET /api/v1/demo/yolo-restaurant/status
GET /api/v1/demo/yolo-restaurant/stream
```

Ejemplo de stream:

```text
http://127.0.0.1:8000/api/v1/demo/yolo-person/stream?confidence=0.35&iou=0.5
http://127.0.0.1:8000/api/v1/demo/yolo-restaurant/stream?source=0&image_size=320&inference_stride=3
```

Para usarlo en el dashboard:

```text
VITE_CAMERA_STREAM_URL=http://127.0.0.1:8000/api/v1/demo/yolo-restaurant/stream?source=0&image_size=320&inference_stride=3
```

## Modo restaurante demo

El modo `yolo-restaurant` no decide todavía si una mesa está libre u ocupada. Sirve para validar visualmente en casa o en el local qué reconoce COCO antes de hacer fine-tuning.

Clases activas por defecto:

```text
person, chair, dining table, cup, bottle, wine glass, bowl, fork, knife, spoon, pizza
```

Uso recomendado:

1. enfocar la mesa de casa o del restaurante;
2. verificar si YOLO detecta persona/silla/mesa/vasos;
3. no convertir esas detecciones en eventos de negocio todavía;
4. conectar después con ROI de mesa y reglas temporales.

La decisión operativa correcta no debe ser “YOLO ve una mesa”, sino:

```text
mesa_ocupada = persona_intersecta_roi_mesa durante N segundos con confianza suficiente
```

Esto sigue la separación entre inferencia visual, postprocesado y decisión de negocio recomendada por los índices de *Machine Learning Systems*: pipeline de inferencia, consistencia training-serving, monitorización y evaluación de inferencia.

## Parámetros relevantes

- `model`: pesos del modelo, por defecto `yolo11n.pt`.
- `confidence`: umbral mínimo de confianza.
- `iou`: umbral de supresión de duplicados.
- `image_size`: tamaño de inferencia.
- `max_detections`: máximo de cajas por frame.
- `min_box_area_ratio`: área mínima relativa para descartar detecciones residuales.
- `inference_stride`: ejecuta YOLO cada N frames y reutiliza la última detección en los frames intermedios. Para CPU/local empezar con `3`; si va fluido, bajar a `2` o `1`.

## Optimización CPU aplicada

Los documentos de YOLO revisados no aportan una arquitectura nueva recomendable para implantar desde cero, pero sí refuerzan cuatro decisiones prácticas:

1. usar un modelo pequeño (`yolo11n.pt`);
2. reducir la imagen de inferencia (`image_size=320`);
3. mantener filtrado por clases y NMS;
4. espaciar inferencias en CPU con `inference_stride`.

En RestaurIA el stream mantiene el vídeo continuo, pero YOLO no se ejecuta necesariamente en todos los frames:

```text
si frame_index % inference_stride == 0:
    detecciones = YOLO(frame)
si no:
    reutilizar últimas detecciones
```

Esto reduce carga de CPU y hace más viable la prueba con webcam en portátil básico.

## Postprocesado aplicado

D2L recalca que la detección de objetos no termina en la red: las cajas predichas deben filtrarse y consolidarse. En RestaurIA aplicamos:

1. filtro por clase `person`;
2. filtro por confianza mínima;
3. recorte de cada bounding box al frame real;
4. descarte de cajas degeneradas o demasiado pequeñas;
5. non-maximum suppression por IoU.

Esto reduce ruido antes de convertir detecciones en observaciones operativas de mesa.

## Reglas de uso

- En portátil básico empezar con `yolo11n.pt` e `image_size=320`.
- Mantener `inference_stride=3` en CPU; ajustar solo si el portátil responde bien.
- Para una mesa doméstica, usar `yolo-restaurant` solo como exploración visual.
- No intentar detectar platos/cubiertos como señal principal sin fine-tuning.
- Mantener el conteo de personas separado de la lógica de estado de mesa.
- Conectar después con zonas/ROI para decidir si una persona está asociada a una mesa.

## Señales de alerta

- Ultralytics open source usa AGPL-3.0; revisar antes de comercialización cerrada.
- La primera descarga de pesos puede requerir Internet si el modelo no está en local.
- YOLO puede detectar personas fuera de la mesa; hay que combinarlo con ROI o bottom-center assignment.
- `dining table` de COCO no equivale a “mesa operativa del restaurante”; la mesa real debe venir de configuración/calibración.
- La detección no debe usarse para identificación facial ni trazabilidad nominal.

## Referencias internas al documento

- Capítulo Computer Vision, sección Image Augmentation, página PDF 583.
- Capítulo Computer Vision, sección Fine-Tuning, página PDF 592.
- Capítulo Computer Vision, sección Object Detection and Bounding Boxes, página PDF 598.
- Capítulo Computer Vision, sección Anchor Boxes, página PDF 601.
- Capítulo Computer Vision, sección Predicting Bounding Boxes with Non-Maximum Suppression, página PDF 611.
- Capítulo Computer Vision, sección Multiscale Object Detection, página PDF 615.
- Capítulo Computer Vision, sección Single Shot Multibox Detection, página PDF 622.
- Capítulo Computer Vision, sección Region-based CNNs, página PDF 634.
- *Machine Learning Systems*, secciones del índice: Inference Pipeline, páginas PDF 204-209; Systematic Data Processing y Training-Serving Consistency, páginas PDF 408-417; Inference Metrics, páginas PDF 1091-1094.
- *Computer Vision: Models, Learning, and Inference*, Part I/II, índice: Learning and inference in vision, página 83; Classification models, página 171; Image preprocessing and feature extraction, página 325; HOG descriptor para peatones, páginas 343-344; Temporal models/Kalman filter, páginas 537-540.
- `IJES-V11-21s-2025-303.pdf`: no trae índice embebido. Secciones detectadas: Abstract, `1. INTRODUCTION`, `2. Related work`, `2.1 Learning YOLO and CNN Object Detection`, `3. Current methods of detecting moving objects`, `5. RESULT`, `CONCLUSION`. Ideas reutilizadas: OpenCV + YOLO, blob/preprocesado, umbral de confianza, NMS y clases COCO.
- `optimized-yolo-algorithm-for-cpu-to-detect-road-traffic-accident-and-alert-system-IJERTV8IS090056.pdf`: no trae índice embebido. Secciones detectadas: Abstract, `I. INTRODUCTION`, `II. PROBLEM STATEMENT`, `III. OPTIMIZED YOLO ARCHITECTURE AND IMPLEMENTATION`, `IV. RELATED WORK`, `V. CONCLUSION`, `VI. FUTURE SCOPE`. Idea reutilizada: priorizar inferencia viable en CPU con modelo pequeño, entrada reducida y frecuencia de inferencia controlada.
