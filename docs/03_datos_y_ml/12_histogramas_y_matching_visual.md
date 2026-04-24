# Histogramas y matching visual

## Propósito
Definir cómo usar distribuciones estadísticas de imagen y técnicas de matching visual para generar señales de cambio de estado en RestaurIA.

Este documento se centra en:
- comparación de apariencia de una ROI,
- robustez ante cambios visuales graduales,
- búsqueda de similitud entre estados,
- y uso prudente de plantillas u objetos visuales.

## Decisión técnica principal
Los histogramas son útiles en RestaurIA como señal complementaria de bajo coste, especialmente para:
- diferenciar mesa vacía frente a mesa alterada,
- medir cambio global de apariencia de una ROI,
- y reforzar observaciones simples sin depender de detección compleja.

No deben tratarse como única fuente de verdad, porque:
- pierden estructura espacial fina,
- son sensibles a iluminación y composición,
- y pueden confundir cambios distintos con distribuciones parecidas.

## Restricción de uso importante
No se utilizará `color de piel` como señal base del sistema.

Motivo:
- introduce riesgos de sesgo y fragilidad,
- entra en una zona sensible de inferencia,
- y no es necesario para cumplir el objetivo del MVP.

Sí se podrán explorar histogramas de:
- ROI completa,
- fondo de mesa,
- uniformes si existe un caso interno y controlado,
- o apariencia de objetos de servicio,
siempre que tengan utilidad operativa clara y no impliquen etiquetado sensible.

## Qué aporta un histograma en este proyecto
Un histograma resume cuántos píxeles caen en determinados rangos:
- de brillo,
- de color,
- o de otra representación transformada.

En RestaurIA, esto puede servir para:
- comparar una mesa con su referencia vacía,
- detectar alteración visual significativa,
- o medir estabilidad de una zona a lo largo del tiempo.

## Casos de uso realistas para el MVP

### 1. Mesa vacía vs. mesa alterada
Uso:
- guardar una referencia de apariencia de la ROI en estado vacío,
- comparar el histograma actual con la referencia,
- usar la desviación como una señal de ocupación o cambio.

### 2. Detección de cambio sostenido
Uso:
- comparar histogramas entre frames separados temporalmente,
- detectar si la escena se ha estabilizado o sigue cambiando,
- apoyar transiciones de estado.

### 3. Refuerzo ante iluminación variable
Uso:
- combinar histogramas con otras señales,
- detectar cambios suaves de distribución,
- mejorar robustez frente a pequeñas alteraciones visuales.

### 4. Perfiles de mesa por fase de servicio
Uso:
- comparar la apariencia global de una mesa entre estados operativos,
- distinguir entre mesa recién servida, mesa alterada y mesa posiblemente lista para desbarasar,
- y generar señales auxiliares de transición.

Aplicación prudente:
- no usarlo como decisión única,
- sí como indicio complementario si el cambio visual de vajilla y restos es suficientemente estable.

## Comparación de histogramas

### Métodos útiles conceptualmente
- correlación,
- chi-cuadrado,
- intersección,
- Bhattacharyya.

### Recomendación para el proyecto
No fijar de entrada un único método como definitivo.

El baseline debería comparar al menos:
- correlación o intersección para casos simples,
- Bhattacharyya para escenarios con solapamiento parcial,
- y medir cuál ofrece más estabilidad en laboratorio.

## Earth Mover's Distance (EMD)

### Qué aporta
EMD es interesante cuando:
- la distribución cambia de forma gradual,
- el histograma “se desplaza” por iluminación,
- o hace falta una comparación más flexible que la coincidencia bin a bin.

### Valor para RestaurIA
Puede ser útil en fases posteriores o en cámaras difíciles, pero no debe ser el primer paso del MVP por:
- complejidad,
- coste,
- y necesidad de justificar beneficio real frente a comparaciones más simples.

### Decisión
Registrar EMD como técnica de exploración y mejora, no como baseline obligatorio inicial.

### Casos donde merece más atención
EMD puede ser especialmente útil si:
- la cámara inalámbrica introduce cambios moderados de color o balance de blancos,
- la iluminación cambia a lo largo del servicio,
- o los histogramas simples fallan por desplazamiento suave de la distribución.

## Retroproyección

### Qué es útil aquí
La retroproyección puede servir para proyectar sobre el frame qué zonas encajan con un modelo estadístico.

### Uso prudente en RestaurIA
Puede explorarse para:
- localizar regiones con apariencia similar a un modelo de objeto,
- reforzar zonas activas dentro de una ROI,
- o experimentar con áreas de uniforme o elementos de servicio.

### Qué no conviene hacer
- usarla como detector principal de personas,
- basarla en atributos sensibles,
- o asumir robustez suficiente sin validación fuerte.

### Restricción importante
No usar `color de piel` como base del sistema.

Sí puede explorarse, con prudencia, para:
- uniformes de personal si existe un caso interno y controlado,
- objetos o elementos de servicio con apariencia suficientemente estable,
- o máscaras auxiliares de interacción no sensible.

## Matching por plantillas

### Cuándo puede ser útil
La coincidencia de plantillas puede tener valor para:
- objetos relativamente rígidos,
- geometrías estables,
- y escenas controladas.

En RestaurIA, los candidatos naturales serían:
- platos,
- vasos,
- terminales de pago,
- u otros objetos de servicio en escenarios bien acotados.

También puede explorarse para:
- carpeta o cuenta sobre la mesa,
- cubiertos o utensilios muy estables,
- o indicadores visuales de finalización de servicio.

### Limitaciones
No es buena base para:
- personas,
- poses variables,
- o escenas con mucha oclusión y cambios de escala.

### Decisión
Mantener template matching como capacidad de exploración para objetos estáticos, no como centro del MVP.

#### Prioridad operativa potencial
Entre los usos exploratorios, uno de los más interesantes para producto es:
- detección de objetos de servicio asociados a transición de mesa,
- por ejemplo elementos que puedan reforzar el estado `finalizando` o `desbarasar`.

## Cómo encaja esta capa en la arquitectura
Los histogramas y matching visual deben generar señales intermedias, no decisiones finales.

Flujo conceptual:

```text
ROI
  -> preprocesado
  -> histograma o descriptor simple
  -> comparación con referencia o estado previo
  -> score de cambio visual
  -> observación de zona
```

## Señales útiles que esta capa puede producir
- score de similitud con mesa vacía,
- distancia a referencia,
- estabilidad temporal del histograma,
- score de cambio abrupto,
- presencia probable de objeto plantilla,
- y nivel de confianza de la comparación.

## Estrategia recomendada para el MVP

### Baseline
Usar histogramas como señal auxiliar de:
- cambio de apariencia de la ROI,
- comparación con referencia vacía,
- y refuerzo de ocupación.

### Combinación recomendada
No usar histogramas solos.

Combinar con:
- porcentaje de píxeles activos,
- blobs o contornos,
- detección de persona si existe,
- y consistencia temporal.

### Estrategia recomendada para fases posteriores
Cuando el sistema madure, los histogramas y matching pueden apoyar:
- `mesa_lista_para_desbarasar`,
- `interaccion_de_servicio`,
- `fase_de_finalizacion`,
- y cambios visuales asociados a objetos sobre mesa.

## Objetos de servicio: criterio de uso

### Qué merece la pena intentar
Los objetos que más sentido tienen aquí son:
- platos,
- vasos,
- carpeta o cuenta,
- terminal de pago,
- y otros elementos de servicio relativamente estables.

### Qué no conviene prometer pronto
No conviene convertir:
- cubiertos finos,
- utensilios pequeños,
- o vajilla muy variable,
en requisito duro temprano del sistema.

### Decisión de proyecto
Para objetos de servicio, el orden correcto es:
- primero `matching` o señales visuales sencillas en vista controlada,
- luego evaluación de histogramas o descriptores agregados,
- y solo después detectores entrenados si el rendimiento justifica el coste.

## Cómo crear la referencia de mesa vacía
La referencia no debería ser una sola imagen aislada sin control.

Recomendación:
- capturar varias muestras de la mesa vacía,
- en condiciones razonablemente similares,
- y almacenar una referencia robusta o una pequeña colección de referencias.

## Riesgos a vigilar
- confundir cambios de luz con ocupación,
- sensibilidad a objetos pequeños sobre la mesa,
- degradación por sombras largas,
- falsas diferencias por reflejos,
- y exceso de confianza en señales estadísticas sin contexto espacial.

## Recomendaciones de laboratorio
- comparar varias métricas de histogramas en vídeos repetibles,
- medir estabilidad por franja de luz,
- guardar ejemplos donde el histograma falla,
- probar combinación con morfología y ROI bien calibradas,
- y no aceptar una métrica solo porque “parece elegante”.

## Qué entra en el MVP
- histogramas de ROI como señal auxiliar,
- comparación con referencia de mesa vacía,
- score de similitud para apoyar ocupación,
- y estudio de métodos simples de comparación.

## Qué se deja para después
- EMD como técnica más costosa,
- retroproyección avanzada,
- template matching de objetos de servicio,
- y cualquier uso que dependa de escenarios demasiado frágiles o sensibles.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/06_legal_y_riesgos/03_politica_de_uso_aceptable.md`

## Conclusión
El valor de este capítulo para RestaurIA está en ofrecer una forma barata y explicable de medir cambio visual por ROI.

Bien usados, los histogramas pueden reforzar la detección de ocupación y estabilidad de mesa.
Mal usados, pueden convertirse en una señal engañosa o sensible.

Por eso, en el proyecto deben ocupar el lugar correcto:
- señal auxiliar,
- validada con otras evidencias,
- y siempre dentro de una política de uso prudente.
