# Preprocesado ligero con integral image y filtros Haar

## Decisión

Añadir una capa de preprocesado clásico para calcular estadísticas rectangulares de ROIs de mesa en tiempo constante mediante imagen integral.

Esta decisión aterriza el Capítulo 13 de *Computer Vision: Models, Learning, and Inference - Part II* sin introducir dependencias nuevas ni técnicas pesadas. El objetivo no es sustituir a YOLO, sino crear señales baratas para:

- medir contraste local dentro de una mesa,
- detectar cambios simples de ocupación visual,
- estimar actividad sobre la superficie de mesa,
- filtrar ROIs poco informativos antes de lanzar inferencia pesada,
- alimentar reglas o modelos probabilísticos temporales con features interpretables.
- extraer bordes más estables con Canny cuando Sobel sea demasiado ruidoso.

## Encaje en RestaurIA

El módulo vive en `services/vision/classical.py` porque pertenece al carril rápido de visión clásica. Sus salidas pueden alimentar:

- `services/vision/observation_adapter.py`, como feature auxiliar de observación,
- `services/decision/observation_model.py`, como evidencia visual interpretable,
- reglas de mesa vacía/sucia/activa sin ejecutar YOLO en todos los frames.

## Funciones implementadas

- `standardize_intensity`: normaliza una ROI a media cero y varianza unitaria para reducir variaciones de iluminación y ganancia de cámara.
- `integral_image`: genera una imagen integral con padding de un píxel.
- `rectangle_sum`: calcula la suma de intensidades de un rectángulo con cuatro accesos.
- `rectangle_mean`: calcula la media rectangular a partir de la suma integral.
- `haar_like_response`: compara regiones rectangulares positivas y negativas.
- `horizontal_two_rectangle_response`: mide contraste izquierda/derecha.
- `vertical_two_rectangle_response`: mide contraste arriba/abajo.
- `canny_edges`: aplica Gaussian blur, Sobel, supresión de no-máximos y doble umbral con histéresis.

## Uso operativo

Pipeline recomendado para el MVP:

```text
frame
  -> ROI de mesa por slicing NumPy
  -> grayscale
  -> integral image
  -> rectangle_mean / Haar contrast
  -> feature interpretable
  -> regla temporal o modelo de observación
```

Pipeline alternativo para borde estable:

```text
ROI de mesa
  -> grayscale
  -> Canny edge gate
  -> canny_edge_density
  -> smoothing temporal
  -> regla de mesa activa / mesa limpia / mesa con objetos
```

Ejemplo de regla simple:

```text
si edge_density baja
y canny_edge_density baja
y contraste Haar bajo
y detecciones de persona = 0
durante N segundos
entonces mesa probablemente libre
```

## Coste computacional

La imagen integral cuesta `O(H*W)` por ROI. Una vez calculada, cada suma rectangular cuesta `O(1)` independientemente del tamaño del rectángulo.

Canny cuesta `O(H*W)` por ROI y evita lanzar inferencia profunda cuando solo se necesitan señales visuales simples. Es adecuado para portátil básico si se ejecuta sobre ROIs de mesa, no sobre el frame completo.

## Trade-offs

- Es robusto para señales de contraste y brillo, pero no entiende semántica.
- Puede fallar con sombras fuertes, manteles estampados o reflejos.
- No debe usarse como única fuente de verdad para detectar personas.
- Conviene combinarlo con smoothing temporal y reglas de ocupación.
- Canny requiere umbrales calibrables por cámara; no conviene fijarlos como verdad universal.

## Referencias internas

- Capítulo 13, sección 13.1.1: whitening / normalización de intensidad.
- Capítulo 13, sección 13.1.2: ecualización de histograma.
- Capítulo 13, sección 13.1.3: filtrado lineal, Sobel, Laplaciano, Gabor y Haar-like filters.
- Capítulo 13, sección 13.2.1: Canny edge detector.
- Página mostrada como 332 en el PDF: integral image y cálculo de sumas rectangulares en tiempo constante.
