# Monitor ligero de distribution shift visual

## Decisión

Añadir un monitor de distribución visual para detectar cuándo la cámara, iluminación o escena se aleja demasiado del baseline esperado.

La idea procede de *Dive into Deep Learning*, sección *Environment and Distribution Shift*. Para RestaurIA es relevante porque el modelo puede funcionar bien en casa y degradarse en restaurante real por:

- iluminación nocturna,
- sombras,
- posición distinta de cámara,
- mantel o fondo diferente,
- cámara IP con compresión,
- mesa fuera de la zona calibrada.

## Implementación

Módulo:

```text
services/vision/drift.py
```

Features ligeras por frame o ROI:

- media de intensidad,
- desviación estándar,
- densidad de bordes,
- histograma normalizado.

El monitor compara una firma actual contra una firma baseline y devuelve:

- `ok`,
- `warning`,
- `drift`.

## Encaje en el pipeline

Uso recomendado:

```text
ROI de mesa o frame reducido
  -> visual_distribution_signature
  -> VisualDistributionMonitor.compare
  -> warning/drift
  -> bajar confianza o pedir recalibración
```

Esto no sustituye YOLO. Sirve para saber si conviene confiar en YOLO o si hay que revisar cámara/iluminación.

## Parámetros

- `histogram_bins`: granularidad del histograma.
- `edge_threshold`: umbral de borde.
- `warning_score`: umbral de aviso.
- `drift_score`: umbral de drift.

## Aplicación directa

MVP:

- calcular baseline al arrancar con una escena controlada,
- comparar cada cierto número de frames,
- si hay `warning`, mostrar aviso suave,
- si hay `drift`, no generar decisiones fuertes de mesa sin confirmación.

Fase posterior:

- persistir firmas por franja horaria,
- comparar mañana/tarde/noche,
- detectar degradación progresiva de cámara.

## Señales de alerta

- No guardar imágenes completas como baseline salvo necesidad explícita.
- No usar drift como evento operativo de restaurante; es salud del sistema.
- No bloquear todo el pipeline por un drift leve; reducir confianza es mejor que apagar.

## Referencias internas al documento

- D2L, Environment and Distribution Shift, página PDF 193.
- D2L, Types of Distribution Shift, página PDF 194.
- D2L, Correction of Distribution Shift, página PDF 198.
- D2L, Image Augmentation, página PDF 583, como mitigación parcial frente a variaciones visuales.
