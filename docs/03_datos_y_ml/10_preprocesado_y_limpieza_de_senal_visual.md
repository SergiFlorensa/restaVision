# Preprocesado y limpieza de señal visual

## Propósito
Definir el conjunto mínimo de técnicas de preprocesado visual que RestaurIA debe aplicar antes de inferir ocupación, actividad o cambios de estado en una mesa.

En un restaurante real, el sistema se enfrentará a:
- sombras,
- reflejos,
- variaciones de iluminación,
- ruido electrónico de cámara,
- pequeños objetos sobre la mesa,
- y cambios visuales irrelevantes.

El objetivo de esta capa es reducir ese ruido sin destruir la información útil.

## Decisión técnica principal
El preprocesado del MVP debe ser:
- simple,
- trazable,
- medible,
- y suficientemente robusto.

No conviene empezar con pipelines excesivamente complejos. El valor inicial está en una cadena corta y entendible que reduzca falsos positivos y mejore estabilidad.

## Lugar del preprocesado en la arquitectura
El preprocesado pertenece a `services/vision/` y ocurre después de:
- capturar el frame,
- y extraer la ROI o zona.

Flujo recomendado:

```text
frame
  -> ROI
  -> preprocesado
  -> extracción de señales locales
  -> observación de zona
  -> evento
```

## Objetivos del preprocesado
- reducir ruido fino,
- estabilizar diferencias entre frames,
- mejorar máscaras binarias,
- rellenar siluetas o blobs parciales,
- eliminar artefactos pequeños,
- y hacer más fiable la inferencia local por mesa.

## Técnicas prioritarias para el MVP

### 1. Suavizado
El suavizado debe ser la primera herramienta para reducir ruido visual.

#### Gaussiano
Uso recomendado:
- ruido ligero general,
- estabilización temprana,
- preparación antes de umbralización o diferencia.

Equivalente moderno:
- `cv2.GaussianBlur`

#### Mediano
Uso recomendado:
- ruido impulsivo,
- píxeles aislados,
- escenas con pequeños artefactos visuales.

Equivalente moderno:
- `cv2.medianBlur`

#### Regla práctica
Para el MVP:
- empezar con Gaussiano ligero,
- evaluar Mediano si aparecen artefactos puntuales persistentes.

## 2. Conversión de color
No siempre conviene trabajar en BGR.

### Escala de grises
Útil para:
- diferencia simple,
- umbralización,
- reducción de complejidad.

### HSV
Útil cuando:
- la iluminación cambia de forma relevante,
- interesa separar brillo de color,
- o ciertas máscaras mejoran fuera de BGR/gris.

#### Regla práctica
El baseline debe probar primero:
- gris para simplicidad,
- HSV solo si los cambios de luz rompen la estabilidad.

## 3. Umbralización
La umbralización convierte una señal continua en una máscara útil para decisión binaria.

### Umbral fijo
Uso recomendado:
- entornos muy controlados,
- pruebas domésticas estables,
- comparación sencilla contra fondo de referencia.

### Umbral adaptativo
Uso recomendado:
- iluminación desigual,
- sombras locales,
- cambios parciales dentro de la ROI.

#### Regla práctica
En un restaurante, el umbral adaptativo suele ser más robusto que un umbral fijo puro, pero debe medirse porque también puede introducir sensibilidad no deseada.

## 4. Morfología de imagen
Las operaciones morfológicas permiten limpiar máscaras después de la umbralización o segmentación.

### Erosión
Sirve para:
- eliminar puntos pequeños,
- adelgazar regiones espurias,
- reducir ruido residual.

### Dilatación
Sirve para:
- unir fragmentos cercanos,
- expandir regiones útiles,
- hacer visibles blobs rotos.

### Apertura
Secuencia:
- erosión
- dilatación

Uso recomendado:
- eliminar ruido pequeño sin deformar demasiado la región útil.

### Cierre
Secuencia:
- dilatación
- erosión

Uso recomendado:
- rellenar agujeros pequeños,
- compactar la silueta de una persona sentada,
- estabilizar blobs principales.

#### Regla práctica para RestaurIA
Pipeline inicial sugerido:
- umbralización
- apertura ligera si hay demasiado ruido fino
- cierre si la región humana aparece fragmentada

## 5. Reducción de resolución
No toda cámara debe procesarse a resolución completa.

### Cuándo usarla
- hardware modesto,
- latencia alta,
- ROI muy grandes,
- pruebas iniciales.

### Herramientas razonables
- `cv2.resize`
- `cv2.pyrDown`

### Regla práctica
Reducir resolución solo si:
- la señal útil se mantiene,
- y la mejora de latencia es material.

## 6. Segmentación y blobs
En fases iniciales, no hace falta una segmentación sofisticada si una máscara binaria limpia ya permite detectar actividad o masa ocupante.

Sin embargo, ciertas técnicas pueden ser útiles para:
- agrupar regiones conectadas,
- estimar área ocupada,
- y detectar blobs significativos dentro de la mesa.

Aplicación prudente:
- usar conectividad o análisis de contornos antes que sistemas complejos si el caso lo permite.

## 7. Flood Fill
`Flood Fill` no debe ser base del MVP, pero puede ser útil en laboratorio para:
- explorar regiones conectadas desde una semilla,
- inspeccionar cuánto ocupa una mancha activa,
- o validar visualmente agrupaciones en una ROI.

Su papel recomendado:
- herramienta de exploración o depuración,
- no primera opción de producción.

## Señales locales que deberían salir de esta capa
El preprocesado no debe decidir por sí solo el estado de la mesa. Debe producir señales intermedias, por ejemplo:
- porcentaje de píxeles activos,
- número de blobs relevantes,
- área total ocupada,
- cambio respecto a referencia,
- estabilidad temporal de la máscara,
- nivel de ruido residual.

Estas señales alimentarán luego:
- observaciones de zona,
- máquina de estados,
- reglas,
- y modelos simples.

## Pipeline baseline recomendado por ROI

```text
ROI original
  -> conversión a gris
  -> suavizado gaussiano ligero
  -> diferencia o señal local
  -> umbralización
  -> apertura/cierre según ruido observado
  -> cálculo de métricas locales
```

## Cómo decidir qué pipeline usar
No debe elegirse por intuición o gusto técnico.

Cada variante de pipeline debe evaluarse por:
- falsos positivos,
- falsos negativos,
- estabilidad temporal,
- latencia,
- facilidad de explicación,
- y facilidad de ajuste.

## Recomendaciones para la fase de laboratorio
- visualizar cada etapa del pipeline,
- guardar ejemplos de fallo,
- usar trackbars para explorar umbrales,
- documentar qué condiciones rompen cada aproximación,
- y fijar un baseline antes de intentar mejoras complejas.

## Qué no conviene hacer todavía
- encadenar demasiados filtros sin medir,
- complicar la explicación de por qué una mesa cambió de estado,
- optimizar a nivel micro antes de tener métricas,
- o intentar corregir con preprocesado lo que en realidad es un problema de mal encuadre o mala ROI.

## Relación con otros documentos
Este documento complementa:
- `docs/04_software_y_devops/07_opencv_y_adapter_de_captura.md`
- `docs/04_software_y_devops/08_highgui_herramienta_de_calibracion.md`
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`

## Conclusión
El preprocesado visual es el kit de limpieza del MVP.

Su función no es “resolver” la visión por sí solo, sino entregar una señal más estable y menos ruidosa para que la lógica de ocupación, observación y eventos se apoye en algo técnicamente defendible.
