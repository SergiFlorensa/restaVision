# Capa de Deep Learning

## ¿Tiene sentido en este proyecto?
Sí, especialmente en percepción visual y, más adelante, en modelado temporal avanzado.

## Dónde sí usarlo
### Visión
- detección de personas,
- detección de objetos,
- clasificación de estados visuales,
- reconocimiento de acciones.

### Tiempo / secuencia
- patrones temporales complejos,
- anomalías secuenciales,
- modelos de vídeo o secuencia si el dataset lo justifica.

## Dónde no empezar con DL
- dashboard,
- reglas de negocio,
- scoring simple,
- KPIs,
- primeras predicciones estadísticas.

## Librerías / marcos útiles
- PyTorch: https://pytorch.org/get-started/locally/
- OpenCV: https://docs.opencv.org/4.x/d0/d3d/tutorial_general_install.html

## Sobre Ultralytics YOLO
Es muy práctico para prototipado y TFG, pero su licencia open source es AGPL-3.0, lo que implica revisar muy bien el uso si el proyecto se quisiera cerrar o comercializar sin abrir el código.  
Referencias:
- licencia: https://www.ultralytics.com/license
- docs: https://docs.ultralytics.com/

## Alternativa pragmática
### Para TFG
Usar YOLO puede merecer la pena por velocidad de desarrollo.

### Para venta posterior
Revisar licencia con calma o estudiar alternativas según el modelo final de explotación.

## Estrategia recomendada
1. DL en detección visual.
2. ML clásico en predicción de negocio.
3. DL temporal solo si aporta mejora real demostrable.
