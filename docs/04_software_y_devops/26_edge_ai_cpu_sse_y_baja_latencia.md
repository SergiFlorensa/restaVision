# Edge AI en CPU: baja latencia y alertas SSE

## Decisión aplicada

La mejora inmediata no es añadir modelos más grandes ni nuevas dependencias, sino reducir bloqueo entre cámara, inferencia y dashboard.

Para el MVP se implementan dos decisiones:

- captura de último frame disponible para evitar backlog cuando YOLO tarda;
- canal SSE local para que el dashboard reciba cambios de mesa sin esperar al polling.

## Qué se implementa ahora

- `services/events/realtime.py`: bus de eventos en memoria, thread-safe y con descarte del mensaje más antiguo si un cliente va lento.
- `GET /api/v1/demo/table-service/events/stream`: canal `text/event-stream` filtrable por `table_id`.
- `VITE_TABLE_SERVICE_EVENTS_URL`: configuración del dashboard para conectarse por `EventSource`.
- polling de respaldo en el frontend para que el panel siga funcionando si SSE se corta.
- estados semánticos `finishing` y `dirty` cuando exista un modelo con `plate_empty` / `plate_full`.
- scripts batch para recolectar crops de platos, entrenar YOLO y medir latencia local.
- métrica MCC para evaluar estados raros como `dirty` sin caer en precisión engañosa.
- script baseline de ocupación para validar cámara, ROI y YOLO antes de entrenar nada.

## Por qué encaja en el MVP

- no añade Redis, broker ni WebSockets;
- funciona local-first en un portátil;
- transporta solo JSON pequeño, no imágenes;
- separa el vídeo MJPEG del estado operativo de la mesa;
- permite que la pantalla de cámara muestre vídeo limpio y que el registro de mesa reciba avisos estructurados.

## OpenVINO e INT8

OpenVINO sigue siendo una optimización razonable para CPU Intel, pero no se activa como dependencia obligatoria todavía.

La decisión actual es:

1. mantener `ultralytics` como detector funcional de prueba;
2. medir primero latencia real con webcam/DroidCam;
3. exportar a OpenVINO solo cuando el cuello de botella confirmado sea inferencia YOLO;
4. no versionar pesos `.pt`, `.onnx`, `.xml`, `.bin` ni calibraciones reales.

## Configuración recomendada para DroidCam/CPU

```env
VITE_CAMERA_STREAM_URL=http://127.0.0.1:8000/api/v1/demo/table-service/stream?source=http://192.168.1.167:4747/video&table_id=table_01&image_size=256&inference_stride=8&max_detections=15&jpeg_quality=72&text_overlay=false&dirty_grace_seconds=60&finishing_empty_plate_ratio=0.5
VITE_TABLE_SERVICE_ANALYSIS_URL=http://127.0.0.1:8000/api/v1/demo/table-service/analysis?table_id=table_01
VITE_TABLE_SERVICE_EVENTS_URL=http://127.0.0.1:8000/api/v1/demo/table-service/events/stream?table_id=table_01
```

Para probar más rápido en casa puede bajarse `dirty_grace_seconds` a `60`, pero en restaurante real conviene empezar con `180` para evitar que una ida al baño genere una falsa mesa sucia.

## Estados semánticos de mesa

- `seated`: hay cliente, sin señal suficiente de comida o finalización.
- `eating`: hay cliente y comida/plato lleno.
- `finishing`: hay cliente y al menos el 50% de platos semánticos son `plate_empty`.
- `away`: la mesa estaba ocupada, el cliente desaparece y todavía no venció el margen de seguridad.
- `dirty`: no hay cliente, queda residuo de servicio y vence `dirty_grace_seconds`.

## Scripts batch añadidos

```powershell
python tools/collect_plate_state_dataset.py --source video.mp4 --model yolo11n.pt
python tools/train_plate_state_yolo.py --data data/annotations/plate_states/dataset.yaml --device cpu
python tools/benchmark_yolo_latency.py --model yolo11n.pt --image-size 320 --runs 20
python tools/run_table_occupancy_baseline.py --source 0 --roi 120,160,520,430 --display
```

Los scripts escriben en `data/annotations` o `runs`, rutas locales que no deben versionar imágenes reales, vídeos ni pesos.

## Métrica MCC para TFG

La evaluación de estados de mesa debe reportar `accuracy`, `macro_f1` y `matthews_correlation_coefficient`.

Motivo: `dirty` y `finishing` serán clases raras. Un modelo que prediga siempre `ready` puede tener accuracy alta si casi nunca hay mesas sucias, pero MCC bajo. Esto evita una conclusión académica engañosa.

## Señales de alerta

- No usar YOLO `l/x` en portátil básico.
- No activar OpenVINO/NNCF hasta confirmar necesidad real y revisar dependencias.
- No enviar imágenes por SSE; solo eventos y análisis JSON.
- No procesar vídeo completo a alta resolución si el objetivo es una mesa concreta.
