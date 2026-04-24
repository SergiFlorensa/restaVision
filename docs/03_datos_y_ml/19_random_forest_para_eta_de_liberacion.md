# Random Forest para ETA de liberación

## Propósito
Definir cómo entrenar y usar un modelo de bosque aleatorio para estimar el tiempo restante de liberación de una mesa en RestaurIA.

Este documento concreta la estrategia de ML para uno de los objetivos más importantes del proyecto:
- estimar cuántos minutos faltan para que una mesa quede libre.

## Decisión técnica principal
La idea del capítulo es correcta:
- para ETA necesitamos **regresión**,
- no clasificación.

Pero en RestaurIA no se implementará esta capa con la API clásica `CvRTrees` de OpenCV.

La adaptación recomendada es:
- usar `RandomForestRegressor` de `scikit-learn`,
- mantener persistencia versionada del modelo,
- y documentar features, target y métricas con trazabilidad.

## Qué problema exacto estamos modelando
Antes de entrenar, hay que fijar con precisión el objetivo.

En RestaurIA hay dos formulaciones válidas:

### Opción A. Duración total de sesión
Objetivo:
- predecir cuánto durará la sesión completa desde que empieza.

### Opción B. Tiempo restante
Objetivo:
- dado el estado actual de una mesa activa, predecir cuántos minutos faltan para su liberación.

## Decisión recomendada
Para el producto, la formulación más útil es la **Opción B: tiempo restante**.

Porque responde directamente a la pregunta operativa:
- “¿cuánto falta para que esta mesa se libere?”

## Unidad de entrenamiento
Cada fila del dataset debe representar una observación temporal de una mesa activa.

Ejemplo:
- una instantánea de la mesa cada `n` segundos o cada cambio de estado relevante.

Cada fila debería incluir:
- features observadas en ese instante,
- y como target el tiempo real restante hasta la liberación de esa sesión.

## Variables candidatas

### Variables de sesión
- `table_id` o grupo derivado si tiene sentido,
- tamaño inicial del grupo,
- ocupación actual estimada,
- tiempo transcurrido,
- duración media histórica de sesiones similares,
- número de cambios de estado ya ocurridos.

### Variables temporales
- hora del día,
- día de la semana,
- tramo de servicio,
- festivo o no festivo.

### Variables operativas
- estado actual de mesa,
- tiempo desde último evento relevante,
- actividad reciente en la ROI,
- densidad global del local,
- presión operativa agregada si está disponible.

### Variables históricas o derivadas
- desviación respecto a la media esperada,
- percentil temporal dentro de la sesión,
- tasa de cambio reciente,
- tendencia del conteo de personas.

## Variables categóricas y numéricas
El concepto del capítulo sigue siendo válido:
- algunas variables son numéricas,
- otras categóricas.

### Implementación moderna
En `scikit-learn`, esto se traduce en:
- codificación previa de categorías,
- o pipelines con preprocesado explícito.

Ejemplos de variables categóricas:
- zona,
- tramo de servicio,
- día tipo,
- estado de mesa.

Ejemplos de variables numéricas:
- tiempo transcurrido,
- número de personas,
- área ocupada,
- score visual,
- densidad del local.

## Configuración del modelo

### Parámetros importantes
Un bosque aleatorio para ETA debería exponer y versionar al menos:
- `n_estimators`
- `max_depth`
- `min_samples_split`
- `min_samples_leaf`
- `max_features`
- `bootstrap`
- `oob_score` si se usa
- `random_state`

### Recomendaciones prácticas iniciales
- empezar con un número moderado de árboles,
- permitir árboles suficientemente profundos pero no ilimitados por defecto,
- medir `oob_score` solo si el esquema de entrenamiento lo justifica,
- y comparar varias configuraciones simples antes de optimizar.

### Sobre `max_features`
La regla de “raíz cuadrada del número de variables” puede ser una buena heurística de exploración, pero no debe fijarse como dogma.

En regresión conviene probar al menos:
- `sqrt`,
- una fracción razonable del total,
- o el valor por defecto del modelo elegido,
y medir cuál generaliza mejor.

## Importancia de variables
La importancia de variables sí es una ventaja clara de Random Forest para este proyecto.

Nos permite:
- explicar por qué el modelo predice cierto ETA,
- entender qué señales del negocio pesan más,
- eliminar features poco útiles,
- y mantener el sistema interpretable.

## Persistencia y trazabilidad
Cada modelo de ETA debe persistirse con:
- versión,
- fecha,
- features usadas,
- target definido,
- ventana temporal del dataset,
- hiperparámetros,
- métricas de validación,
- y referencia al conjunto de datos.

## Entrenamiento recomendado

### Paso 1. Construir dataset temporal
Cada fila representa una mesa en un instante.

Target:
- minutos restantes reales hasta `mesa_liberada`.

### Paso 2. Separar datos sin fuga temporal
No conviene mezclar observaciones futuras en entrenamiento si luego se van a predecir escenarios posteriores.

Recomendación:
- usar separación temporal o por bloques de sesiones.

### Paso 3. Entrenar baseline
Comparar primero contra:
- media histórica,
- media por tamaño de grupo,
- media por franja,
- o regla simple basada en tiempo transcurrido.

### Paso 4. Entrenar Random Forest
Entrenar el modelo sobre features ya validadas y medir:
- MAE,
- RMSE,
- error por tramo horario,
- error por tamaño de grupo,
- y error en colas altas y bajas.

### Paso 5. Inspeccionar importancia de variables
Si el modelo depende demasiado de una variable espuria o débil, eso debe revisarse antes de pasar a producción.

## Predicción en tiempo real
Para una mesa activa, el sistema debe:
1. construir el vector de features actual,
2. validarlo,
3. invocar el modelo,
4. obtener un ETA en minutos,
5. y opcionalmente acompañarlo de contexto o rango.

### Regla de frecuencia
El ETA no debe recalcularse necesariamente en cada frame.

Recomendación:
- recalcular por evento relevante,
- por ventana temporal razonable,
- o por cambio material de señales,
para reducir latencia y evitar inestabilidad visual.

## Recomendación operativa
No mostrar el ETA como una verdad exacta.

Debe presentarse como:
- estimación,
- rango,
- o tiempo esperado con nivel de confianza razonable.

## ETA puntual vs ETA probabilístico

### Qué conviene perseguir
Aunque el primer MVP pueda empezar mostrando un único ETA puntual, el objetivo maduro debería ser poder expresar también incertidumbre.

Ejemplos útiles:
- probabilidad de liberar antes de `x` minutos,
- rango probable,
- percentil 50 y percentil 80,
- o banda de confianza operativa.

### Por qué importa
En negocio, una estimación como:
- `12 min`
es menos honesta que:
- `entre 10 y 18 min`,
- o `70% de probabilidad de liberar antes de 15 min`.

### Decisión
El MVP puede arrancar con ETA puntual.
La evolución correcta del producto es hacia un ETA probabilístico o, al menos, intervalar.

## Qué no asumir sobre el tiempo restante

### Advertencia importante
No conviene suponer que el tiempo restante de una mesa siga una lógica exponencial con falta de memoria.

En restauración real, el tiempo restante suele depender de:
- cuánto tiempo ha transcurrido ya,
- en qué fase va la mesa,
- tamaño y comportamiento del grupo,
- contexto horario,
- y eventos recientes observados.

### Consecuencia para el modelo
Por eso el dataset de ETA debe conservar variables como:
- tiempo transcurrido,
- estado actual,
- eventos recientes,
- y contexto operativo,
en lugar de apoyarse en una hipótesis memoryless simplificada.

## Riesgos a vigilar
- fuga temporal en el dataset,
- target mal definido,
- features disponibles en entrenamiento pero no en producción,
- importancia de variables engañosa por correlaciones espurias,
- y exceso de confianza en estimaciones muy inestables.

## Qué entra en el MVP
- dataset preparado para ETA,
- baseline estadístico,
- Random Forest como primer modelo serio de regresión,
- importancia de variables,
- persistencia versionada,
- y evaluación rigurosa antes de exponer el ETA al usuario.

## Qué se deja para después
- optimización intensiva de hiperparámetros,
- ensembles complejos,
- incertidumbre probabilística avanzada,
- y modelos temporales más sofisticados.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/18_ml_clasico_y_modelado_predictivo.md`
- `docs/03_datos_y_ml/04_machine_learning.md`
- `docs/07_ejecucion/03_plan_de_validacion.md`
- `docs/04_software_y_devops/10_estrategia_de_latencia_y_rendimiento.md`

## Conclusión
Random Forest es uno de los mejores candidatos clásicos para el ETA de liberación porque ofrece:
- buen rendimiento inicial,
- robustez,
- tolerancia a relaciones no lineales,
- y una explicabilidad razonable para negocio.

Su valor en RestaurIA no está en “adivinar” mágicamente el futuro, sino en transformar observaciones acumuladas en una estimación útil, medible y defendible para la operación.
