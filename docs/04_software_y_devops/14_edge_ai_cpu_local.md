# Edge AI local en CPU para RestaurIA

## Propósito
Convertir las recomendaciones de `Edge-AI-Engineering.pdf` y `Machine Learning Systems` en decisiones aplicables al MVP de RestaurIA: una cámara, una mesa, un portátil convencional y ejecución local sin nube.

La prioridad no es añadir más modelos, sino reducir latencia, acotar consumo de CPU/RAM y mantener trazabilidad entre cámara, observación, evento y dashboard.

## Decisión de aplicación
Se aplican primero las piezas de bajo riesgo y alto impacto:
1. captura desacoplada de OpenCV,
2. buffer de último frame para evitar lag acumulado,
3. cascada ligera con filtro de movimiento antes de inferencia pesada,
4. política de salto de frames cuando la CPU esté caliente,
5. modelo de exportación optimizado a ONNX/OpenVINO/INT8 como objetivo de despliegue.

No se aplican todavía:
- FOMO,
- ExecuTorch,
- NCNN,
- distilación,
- pruning,
- operator fusion manual,
- ni C++.

Esas técnicas pueden tener valor, pero son fase 2 o fase 3 porque aumentan coste de validación y riesgo de licencias sin ser necesarias para demostrar el MVP.

## Módulos de software

### `services/vision/capture.py`
Responsable de abrir una cámara, webcam o vídeo mediante OpenCV y entregar `FramePacket`.

Clases:
- `CaptureConfig`: fuente, identificador, resolución objetivo y buffer.
- `FramePacket`: frame, timestamp, índice, fuente, ancho y alto.
- `OpenCVCaptureAdapter`: ciclo de vida `open/read/close`.

Aplicación:
- configurar cámara IP o webcam a 1280x720,
- fijar buffer a 1 cuando OpenCV lo permita,
- mantener metadatos temporales para sesiones, ETA y depuración.

### `services/vision/realtime.py`
Responsable de evitar backlog y degradar carga cuando el portátil se caliente.

Clases:
- `LatestItemBuffer`: conserva solo el último paquete.
- `FrameSkippingConfig`: define frecuencia normal y frecuencia degradada.
- `FrameSkippingPolicy`: decide si un frame se procesa o se descarta.

Aplicación:
- el hilo de captura no debe esperar a la IA,
- el worker consume siempre el frame más reciente,
- si CPU >= 90%, procesar 1 de cada 3 frames como degradación controlada.

### `services/vision/motion.py`
Responsable de decidir si merece la pena ejecutar inferencia pesada.

Clases y funciones:
- `MotionGateConfig`: umbral de diferencia por píxel y porcentaje mínimo de cambio.
- `MotionDecision`: resultado explicable de la decisión.
- `MotionGate`: mantiene estado entre frames.
- `detect_motion()`: versión funcional para pruebas y notebooks.

Aplicación:
- si el cambio de píxeles es menor del 5%, no se ejecuta YOLO,
- se evita gastar CPU cuando la sala está estática,
- el primer frame sí activa inferencia para obtener estado inicial.

## Algoritmos y matemáticas aplicables

### Cascada de clasificadores
Primero se ejecuta un filtro barato y solo después el modelo caro:

```text
frame 720p
  -> diferencia absoluta contra frame previo
  -> ratio de píxeles cambiados
  -> si ratio >= umbral, ejecutar detector
  -> si no, reutilizar estado temporal y evitar inferencia
```

Fórmula:

```text
motion_ratio = count(abs(frame_t - frame_t-1) >= pixel_delta_threshold) / total_pixels
```

Decisión inicial:
- `pixel_delta_threshold = 25`
- `motion_ratio_threshold = 0.05`

### Pipeline asíncrono con cola de tamaño 1
La latencia operativa se controla descartando frames antiguos:

```text
hilo captura -> LatestItemBuffer(max=1) -> worker inferencia -> eventos -> dashboard
```

Esto prioriza presente sobre exhaustividad. Para sala, ver el último estado importa más que procesar todos los frames.

### Throughput efectivo
El rendimiento real queda limitado por la etapa más lenta:

```text
T_sistema = min(T_captura, T_preprocesado, T_inferencia, T_postprocesado)
```

Por eso se separan frecuencias:
- captura puede ir a 25-30 FPS,
- observación puede ir a 5-10 FPS,
- ETA puede recalcularse por evento o cada pocos segundos.

### INT8 y batch size 1
Para CPU de portátil:
- batch size = 1 por latencia,
- evitar FP16 salvo benchmark real,
- evitar FP32 como formato final,
- preferir ONNX Runtime u OpenVINO INT8.

## Configuración recomendada para el MVP

### Cámara
- Resolución de captura: 1280x720.
- Códec recomendado: H.264.
- Evitar H.265 en portátil básico si satura decodificación.
- Cámara fija con iluminación estable.

### Inferencia
- Entrada del modelo: 640x640.
- Umbral de confianza inicial: 0.25-0.40.
- NMS: 0.45-0.50.
- Batch: 1.
- Runtime objetivo: ONNX Runtime u OpenVINO.

### Rendimiento
- FPS procesados iniciales: 5-10.
- Buffer de captura: 1.
- Salto térmico: 1 de cada 3 frames si CPU >= 90%.
- ETA: por evento o ventana temporal, no por frame.

## Patrones de arquitectura

### Separación por capas
- `apps/worker/`: orquesta captura, gating, inferencia y envío al servicio.
- `services/vision/`: captura, buffer, movimiento, geometría, detecciones y observaciones.
- `services/events/`: FSM, eventos y sesiones.
- `services/prediction/`: ETA baseline.
- `data/` y `models/`: datasets y artefactos no pesados versionados solo como metadatos.
- `infra/`: scripts, base local y despliegue.

### Abstracción del detector
El detector no debe quedar acoplado a YOLO. El contrato estable debe ser:

```text
FramePacket -> list[ScoredDetection] -> DetectionToObservationAdapter -> TableObservation
```

Así se puede cambiar `.pt`, ONNX, OpenVINO o un detector clásico sin reescribir eventos.

### Degradación controlada
El sistema no debe fallar de golpe si la CPU no llega. Debe:
- bajar frecuencia de inferencia,
- saltar frames,
- mantener último estado estable,
- registrar latencia y motivo de descarte.

## Métricas obligatorias

### Por frame
- tiempo de captura,
- tiempo de preprocesado,
- tiempo de inferencia,
- tiempo de postprocesado,
- latencia end-to-end,
- decisión del motion gate,
- frame procesado o descartado.

### Por sistema
- FPS capturados,
- FPS procesados,
- uso de CPU,
- uso de RAM,
- número de frames descartados,
- latencia p50/p95,
- falsos ocupados,
- falsos vacíos,
- estabilidad de sesión a 30-60 minutos.

### Por modelo
- formato del artefacto,
- versión,
- resolución de entrada,
- confianza media,
- latencia media,
- latencia p95,
- precisión funcional por mesa.

## Exportación de modelo

Objetivo recomendado:

```powershell
yolo export model=yolo11n.pt format=openvino int8=True
```

Alternativa:

```powershell
yolo export model=yolo11n.pt format=onnx
```

Regla de proyecto:
- no versionar `.pt`, `.onnx`, carpetas OpenVINO ni pesos cuantizados si son pesados,
- guardar solo metadatos de versión en `models/metadata/`,
- revisar licencia de Ultralytics antes de cualquier uso comercial.

## Aplicación concreta a cámara + portátil + restaurante

1. La cámara captura a 720p para mantener buena imagen de supervisión.
2. El worker conserva solo el último frame para evitar retraso acumulado.
3. El motion gate decide si hay cambio visual suficiente.
4. Si no hay cambio, se evita YOLO y se conserva el estado suavizado.
5. Si hay cambio, el frame se redimensiona a 640x640 para inferencia.
6. El detector produce `ScoredDetection`.
7. `DetectionToObservationAdapter` aplica NMS, asigna personas a zonas y genera `TableObservation`.
8. La FSM abre, mantiene o cierra sesiones de mesa.
9. La persistencia registra eventos, latencia, versión de modelo y timestamp.
10. El dashboard consulta estado actual e historial sin tocar frames crudos.

## Orden de implementación
1. `LatestItemBuffer` + `MotionGate`.
2. Worker local con OpenCV y una fuente de vídeo.
3. Adaptador de detector simulado o clásico para validar flujo.
4. Detector YOLO exportado a ONNX/OpenVINO.
5. Métricas de latencia p50/p95.
6. Degradación automática por CPU.
7. Calibración INT8 con imágenes reales del salón.

## Geometría y resolución
La geometría de zonas debe ser estable aunque cambie la resolución del stream.

Implementación:
- `FrameResolution` define el espacio de calibración y ejecución.
- `PolygonRescaler` aplica escalado lineal entre resoluciones.
- `normalize_polygon()` permite guardar polígonos en coordenadas 0-1.
- `same_aspect_ratio()` detecta cambios que pueden invalidar la calibración.

Regla práctica:
- reescalar polígonos al iniciar o cuando cambie la resolución,
- no recalcularlo en cada frame,
- alertar si el aspect ratio cambia de forma relevante.

## Criterio de aceptación
La aplicación de esta estrategia se considera válida cuando:
- el sistema procesa una cámara o vídeo sin backlog visible,
- el estado de una mesa no oscila por frames aislados,
- el pipeline puede funcionar a 5-10 FPS procesados en portátil,
- la inferencia pesada no se ejecuta en frames estáticos,
- y cada evento conserva timestamp, cámara, zona, mesa y metadatos de latencia.

## Relación con documentos existentes
- `docs/04_software_y_devops/07_opencv_y_adapter_de_captura.md`
- `docs/04_software_y_devops/09_video_to_observation_adapter.md`
- `docs/04_software_y_devops/10_estrategia_de_latencia_y_rendimiento.md`
- `docs/04_software_y_devops/12_pipeline_ligero_para_camara_unica.md`
- `docs/04_software_y_devops/13_maria_flujo_doble_velocidad.md`
- `docs/04_software_y_devops/05_licencias_y_decisiones_de_stack.md`

## Decisión final
Para el MVP, la extracción más importante de los documentos no es introducir más IA, sino hacer que el pipeline sea estable en hardware modesto:
- local-first,
- CPU-first,
- buffer de último frame,
- inferencia selectiva,
- exportación optimizada,
- métricas desde el primer worker.
