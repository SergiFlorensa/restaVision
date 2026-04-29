# Pose humana opcional para pruebas de sala

## Decisión aplicada

Se añade un modo opcional de estimación de pose 2D con YOLO pose. No sustituye al detector principal de ocupación ni al análisis de mesa.

Motivo: el survey de HPE distingue entre 2D, 3D, monocular, multi-persona y vídeo. Para RestaurIA, lo útil ahora es solo 2D monocular/multi-persona como visualización y señal auxiliar. 3D HPE, GCNs, multi-view y modelos complejos quedan fuera del MVP.

## Qué aporta al software

- Visualización más interpretable que una caja: esqueleto corporal sobre la persona.
- Silueta aproximada barata mediante convex hull de keypoints visibles.
- Base futura para gestos simples como mano levantada sin reconocimiento facial.
- Modo aislado `/api/v1/demo/yolo-pose/stream` para no afectar la latencia del stream principal.

## Configuración recomendada CPU

```env
VITE_CAMERA_STREAM_URL=http://127.0.0.1:8000/api/v1/demo/yolo-pose/stream?source=0&image_size=256&inference_stride=6&jpeg_quality=72&draw_silhouette=true&draw_boxes=false
```

Parámetros:

- `image_size=256`: reduce coste en CPU.
- `inference_stride=6`: ejecuta pose cada 6 frames y reutiliza resultado intermedio.
- `draw_boxes=false`: evita volver al recuadro clásico.
- `draw_silhouette=true`: muestra silueta aproximada sin segmentación pesada.

## Límites

- No usar 3D HPE en el MVP.
- No usar segmentación pesada para silueta real si la CPU no aguanta.
- No activar pose por defecto en el dashboard operativo hasta medir FPS.
- No usar pose para identificar personas; solo postura anónima.

## Referencias internas al PDF

- Sección II: preliminares, heatmaps, datasets y métricas.
- Sección III: 2D Human Pose Estimation.
- Sección III-C: vídeo 2D HPE y uso temporal.
- Sección V: aplicaciones en análisis de acción y tracking humano.
- Sección VI: retos de oclusiones, robustez y coste computacional.
