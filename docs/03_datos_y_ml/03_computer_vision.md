# Capa de Computer Vision

## Objetivo
Convertir la imagen en señales estructuradas útiles para operación.

## Capacidades candidatas
### MVP
- detección de personas,
- conteo,
- ocupación de mesa,
- zonas de interés.

### Intermedio
- tracking multiobjeto,
- asociación persona↔mesa,
- detección de entrada/salida de zona.

### Avanzado
- detección de objetos relevantes,
- acciones simples,
- multi-cámara,
- fusión temporal.

## Técnicas y conceptos
- object detection,
- segmentation,
- pose estimation,
- multi-object tracking,
- re-identification,
- action recognition.

## Qué problemas resuelve
- saber cuántas personas hay,
- saber dónde están,
- saber cuándo una mesa pasa de libre a ocupada,
- saber cuándo empieza a vaciarse.
- reforzar fases de servicio mediante objetos visuales relevantes.

## Nota de diseño
No buscar perfección visual total. Buscar **suficiente fiabilidad** para ayudar en decisiones.

## Documentos complementarios
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/03_datos_y_ml/12_histogramas_y_matching_visual.md`
- `docs/03_datos_y_ml/13_contornos_y_metricas_geometricas.md`
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`
- `docs/03_datos_y_ml/15_tracking_y_movimiento_temporal.md`
- `docs/03_datos_y_ml/20_segmentacion_avanzada_y_restauracion.md`
- `docs/03_datos_y_ml/21_autosetup_geometrico_y_asignacion_espacial.md`
- `docs/03_datos_y_ml/23_objdetect_y_features_aprendidas.md`
- `docs/03_datos_y_ml/25_iou_nms_y_asignacion_espacial.md`
