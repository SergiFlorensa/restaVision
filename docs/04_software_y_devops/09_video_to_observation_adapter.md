# Video-to-Observation Adapter

## Propósito
Definir el componente que convierte un flujo de vídeo en observaciones estructuradas utilizables por RestaurIA.

Este adaptador es la pieza que conecta:
- la captura de frames,
- la geometría de mesas y zonas,
- el preprocesado visual,
- y la generación de señales observables para el motor de eventos.

## Decisión técnica principal
La idea del capítulo es correcta: hace falta un adaptador que envuelva la captura y entregue unidades procesables.

Pero en RestaurIA se implementará con la API moderna del stack:
- `cv2.VideoCapture`
- `numpy.ndarray`
- objetos estructurados de frame y observación
- y separación clara entre captura, preprocesado y dominio

No se implementará como una traducción literal de:
- `CvCapture`
- `cvQueryFrame`
- `cvSetImageROI`
- `cvReleaseCapture`

## Qué es una observación
Una observación no es solo un frame.

Una observación es una unidad estructurada que resume qué ve el sistema en una zona concreta en un instante.

Ejemplos de contenido razonable:
- `camera_id`
- `frame_index`
- `timestamp`
- `zone_id`
- `table_id`
- `people_count_estimate`
- `foreground_ratio`
- `largest_blob_area`
- `occupancy_score`
- `debug_artifacts_ref`

## Responsabilidad del adaptador
El `Video-to-Observation Adapter` debe:
- abrir la fuente de vídeo,
- leer frames de forma controlada,
- iterar sobre zonas activas,
- recortar o enmascarar la región relevante,
- aplicar preprocesado,
- producir señales intermedias,
- y devolver observaciones estructuradas.

No debe:
- decidir estados finales de negocio,
- generar reglas operativas complejas,
- ni asumir la lógica de mesa por completo.

## Flujo conceptual

```text
fuente de vídeo
  -> frame
  -> corrección geométrica opcional
  -> iteración por zonas
  -> extracción de ROI o máscara
  -> preprocesado
  -> señales visuales locales
  -> observación estructurada
  -> motor de eventos
```

## Fuentes de entrada soportadas

### Archivo de vídeo
Uso:
- pruebas reproducibles,
- tuning,
- validación,
- demos controladas.

### Cámara en vivo
Uso:
- laboratorio doméstico,
- piloto local,
- operación real.

### Regla de diseño
El adaptador debe exponer la misma interfaz independientemente de si la fuente es:
- archivo,
- webcam,
- o futura cámara IP/RTSP.

## Bucle de captura

### Comportamiento esperado
El adaptador debe trabajar sobre un bucle de lectura secuencial:
- leer frame,
- validar fin o error,
- enriquecer con metadatos,
- y pasarlo al pipeline local de observación.

### Control temporal
No conviene acoplar el sistema a “procesar todo lo que llegue” sin control.

Debe existir capacidad para:
- limitar FPS efectivo,
- muestrear cada `n` frames,
- pausar,
- y registrar latencia de procesamiento.

## Relación con las ROIs
El adaptador no debe procesar el restaurante completo de forma indiscriminada en cada etapa.

Debe usar:
- `roi_bbox`,
- geometría de zona,
- o máscara poligonal,
para producir una observación local por mesa o zona.

### Patrón recomendado
Para cada frame:
1. cargar zonas activas,
2. extraer vista local,
3. aplicar pipeline local,
4. producir una observación por zona.

## Pipeline de pre-observación
Antes de producir observaciones, el adaptador debe poder ejecutar una cadena mínima de limpieza:
- suavizado,
- conversión de color,
- corrección geométrica opcional,
- sustracción de fondo o comparación con referencia,
- morfología,
- contornos o componentes.

El resultado de esta fase no es todavía un evento, sino una colección de señales.

## Salidas del adaptador

### Nivel 1. Frame packet
Unidad base con:
- `frame`
- `timestamp`
- `frame_index`
- `source_id`
- `width`
- `height`

### Nivel 2. Zone observation
Unidad por zona con:
- `zone_id`
- `table_id`
- `timestamp`
- `signals`
- `confidence`
- `debug_refs`

### Nivel 3. Batch de observaciones
Conjunto de observaciones derivadas del mismo frame.

Esto es útil porque:
- mantiene coherencia temporal,
- facilita persistencia,
- y desacopla visión de negocio.

## Diseño recomendado de interfaces

### Interfaz conceptual de captura
```python
capture = CaptureAdapter(source=config.source)
frame_packet = capture.read()
```

### Interfaz conceptual de observación
```python
adapter = VideoToObservationAdapter(
    capture=capture,
    zone_registry=zone_registry,
    vision_pipeline=vision_pipeline,
)

observation_batch = adapter.next()
```

## Relación con `services/vision/`
Este componente debería vivir lógicamente en `services/vision/` y coordinar:
- captura,
- corrección geométrica,
- ROIs,
- preprocesado,
- y extracción de señales.

## Relación con `apps/worker/`
El worker debe:
- iniciar el adaptador,
- consumir batches de observaciones,
- pasarlos al motor de eventos,
- persistir resultados,
- y gestionar el ciclo de vida del proceso.

## Gestión de errores y cierre
El adaptador debe manejar correctamente:
- fin de stream,
- desconexión de cámara,
- frame nulo o corrupto,
- y cierre de recursos.

### Regla práctica
Debe existir una ruta explícita de:
- inicialización,
- ejecución,
- parada,
- liberación.

## Requisitos de estabilidad
Para que el adaptador sea válido en el proyecto, debe:
- no filtrar memoria,
- no acumular buffers sin límite,
- cerrar bien la cámara o archivo,
- y mantener trazabilidad entre frame y observación.

## Requisitos de explicabilidad
Cada observación debería poder explicar, al menos en modo debug:
- qué ROI se usó,
- qué señales visuales la generaron,
- y qué artefactos intermedios estaban presentes.

## Modo debug
El adaptador debe poder trabajar en un modo técnico en el que se exporten:
- frame anotado,
- ROI por zona,
- máscara,
- blobs o contornos,
- y señales calculadas.

Esto es clave para:
- validar reglas,
- ajustar umbrales,
- y explicar por qué se detectó ocupación.

## Qué entra en el MVP
- soporte a archivo y cámara,
- lectura controlada de frame,
- iteración por zonas activas,
- recorte por ROI,
- preprocesado mínimo,
- producción de observaciones estructuradas,
- y cierre limpio de recursos.

## Requisito temporal explícito
Cada observación debe arrastrar metadatos temporales suficientes para:
- duración de sesión,
- validación de movimiento,
- ETA,
- y consistencia entre fuentes de señal.

Mínimo:
- `timestamp`
- `frame_index`
- `source_id`

## Requisito explícito de rendimiento
El adaptador debe poder desacoplar:
- frecuencia de captura,
- frecuencia de observación por zona,
- y frecuencia de inferencia de ETA.

Referencia complementaria:
- `docs/04_software_y_devops/10_estrategia_de_latencia_y_rendimiento.md`

## Qué se deja para después
- batching asíncrono complejo,
- multiproceso por cámara,
- múltiples cámaras simultáneas en un solo worker,
- y optimizaciones avanzadas si aún no están justificadas por métricas.

## Relación con otros documentos
Este documento complementa:
- `docs/04_software_y_devops/07_opencv_y_adapter_de_captura.md`
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`

## Conclusión
El `Video-to-Observation Adapter` es el puente entre visión y dominio.

Su trabajo no es “ver vídeo”, sino transformar vídeo en observaciones trazables por mesa y por instante. Si esta pieza está bien diseñada, el resto del sistema puede crecer con orden; si está mal planteada, todo queda acoplado a frames crudos y lógica difícil de mantener.
