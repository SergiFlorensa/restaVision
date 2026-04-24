# ML clásico y modelado predictivo

## Propósito
Definir cómo debe usar RestaurIA el aprendizaje automático clásico para convertir observaciones visuales y eventos operativos en:
- predicciones,
- clasificaciones,
- scores,
- y estimaciones explicables de utilidad real.

Este documento toma los conceptos del capítulo de Machine Learning y los adapta al stack y a la estrategia real del proyecto.

## Decisión técnica principal
Aunque OpenCV incluye algoritmos clásicos de ML, RestaurIA no debe basar su capa de modelado en la API antigua de ML de OpenCV.

La decisión recomendada para el proyecto es:
- usar OpenCV para visión y extracción de señales,
- y usar librerías modernas de ML para entrenamiento y predicción.

Herramientas preferidas:
- `scikit-learn` para baseline y experimentación robusta,
- `LightGBM` o `XGBoost` si aportan mejora clara,
- y persistencia reproducible de modelos y metadatos.

## Qué papel juega el ML en RestaurIA
El ML no es el punto de entrada del sistema.

Antes del ML deben existir:
- captura fiable,
- zonas definidas,
- observaciones visuales útiles,
- eventos persistidos,
- estados de mesa coherentes,
- y un dataset mínimamente estructurado.

El ML entra para responder mejor preguntas como:
- cuánto puede durar una sesión,
- cuánto tiempo queda para liberar una mesa,
- qué observación es anómala,
- qué riesgo operativo merece atención.

Importante:
- no todo problema de predicción exige ML,
- y la analítica de capacidad puede apoyarse primero en teoría de colas y estadística descriptiva antes de pasar a modelos entrenados.

## Problemas de ML prioritarios

### 1. Clasificación binaria o multiclase de estado
Uso:
- reforzar mesa libre/ocupada,
- o clasificar estados intermedios cuando haya suficientes datos.

### 2. Regresión de duración total
Uso:
- estimar duración esperada de una sesión completa.

### 3. Regresión de tiempo restante
Uso:
- ETA de liberación de mesa.

### 4. Detección de anomalías
Uso:
- sesiones raras,
- tiempos muy fuera de patrón,
- comportamiento operacional anómalo.

## Orden correcto de adopción

### Fase 1
- baseline estadístico,
- medias históricas,
- reglas simples.

### Fase 2
- regresión y clasificación clásicas,
- Random Forest,
- Gradient Boosting,
- modelos explicables y comparables.

### Fase 3
- modelos más refinados si mejoran métricas reales,
- detección de anomalías,
- calibración de scores.

## Variables de entrada razonables
Las features deben salir del dominio y de la observación, no de la intuición aislada.

Ejemplos razonables:
- hora del día,
- día de la semana,
- tipo de servicio,
- número inicial de personas,
- número actual de personas,
- tiempo transcurrido,
- estado actual de mesa,
- número de cambios de estado,
- actividad reciente en zona,
- densidad global del local,
- tiempo desde último evento relevante,
- características agregadas de la sesión.

## Variables que no conviene usar de entrada
- atributos sensibles,
- identificadores personales,
- inferencias emocionales débiles,
- señales demasiado inestables o difíciles de explicar,
- y variables que solo existan en laboratorio y no en despliegue real.

## Modelos recomendados por problema

### Para clasificación
Buenos candidatos:
- regresión logística,
- árboles de decisión,
- Random Forest,
- Gradient Boosting.

#### Clasificación binaria de ocupación
Para el problema `libre` vs `ocupada`, los candidatos más razonables son:
- reglas + señales visuales como baseline,
- árboles de decisión para interpretabilidad temprana,
- Random Forest para robustez,
- Gradient Boosting o AdaBoost si mejoran la frontera de decisión con coste asumible.

Regla práctica:
- no introducir boosting solo por tradición,
- compararlo siempre contra un baseline simple y contra Random Forest.

### Para regresión
Buenos candidatos:
- baseline por media,
- regresión lineal,
- Random Forest Regressor,
- Gradient Boosting Regressor,
- LightGBM/XGBoost si aportan mejora clara.

#### ETA de liberación
Para ETA, los candidatos con mejor equilibrio entre valor y mantenibilidad son:
- media histórica segmentada,
- Random Forest Regressor,
- Gradient Boosting,
- LightGBM/XGBoost si la mejora es clara y explicable.

Random Forest destaca por:
- tolerar relaciones no lineales,
- manejar bien features heterogéneas,
- exigir menos preparación extrema,
- y permitir analizar importancia de variables.

### Para anomalías
Buenos candidatos:
- Isolation Forest,
- reglas basadas en percentiles,
- score híbrido con negocio + modelo.

### Para clustering y exploración no supervisada
Buenos candidatos:
- K-Means,
- Gaussian Mixture / EM,
- clustering descriptivo de trayectorias o sesiones.

Uso recomendado:
- exploración,
- segmentación de patrones,
- definición de tipologías de sesión,
- o estudio de zonas de tráfico.

No deben entrar como pieza central del MVP sin una utilidad operativa explícita.

## Qué no conviene usar como punto de partida
- cascadas Haar como centro del conteo moderno del sistema,
- la API antigua de MLL de OpenCV como base del proyecto,
- modelos complejos sin dataset suficiente,
- y pipelines de ML que no puedan explicarse ni mantenerse.

## Flujo correcto de entrenamiento

### Paso 1. Construir dataset
Cada fila debe representar una unidad clara:
- sesión,
- observación temporal,
- evento,
- o instantánea de zona.

### Paso 1.1. Escoger correctamente la variable objetivo
Ejemplos:
- ocupación binaria para clasificación,
- ETA restante para regresión,
- score de rareza para anomalías,
- cluster de comportamiento solo en análisis exploratorio.

### Paso 2. Limpiar y versionar datos
Debe quedar claro:
- qué columnas entran,
- qué transformaciones se aplican,
- qué objetivo se predice,
- y qué conjunto de datos entrenó cada modelo.

### Paso 3. Separar entrenamiento y prueba
Debe existir, al menos:
- train,
- validation,
- test.

Y si el tiempo importa, conviene respetar el orden temporal para evitar fugas de información.

### Paso 4. Evaluar baseline primero
Un modelo complejo solo entra si mejora de forma clara a:
- media histórica,
- regla simple,
- o baseline interpretable.

## Persistencia de modelos
Cada modelo debe poder:
- guardarse,
- cargarse,
- versionarse,
- y asociarse a sus métricas y dataset de entrenamiento.

Metadatos mínimos:
- nombre del modelo,
- versión,
- fecha de entrenamiento,
- objetivo,
- features usadas,
- métrica principal,
- referencia al dataset.

## Preparación de variables

### Regla general
No todos los modelos exigen la misma preparación.

#### Modelos basados en árboles
Ventaja:
- toleran mejor escalas distintas,
- requieren menos normalización explícita,
- y encajan bien con features mixtas del dominio.

#### Modelos sensibles a escala
Si se usan:
- KNN,
- SVM,
- o ciertos métodos basados en distancia,
entonces sí puede ser necesaria estandarización o normalización formal.

### Aclaración importante
La distancia de Mahalanobis no es una técnica de normalización general del dataset.

Su papel correcto sería, en todo caso:
- métrica de distancia,
- detección de observaciones alejadas del patrón,
- o señal auxiliar en anomalías.

No debe documentarse como solución base de normalización de features.

## Diagnóstico y validación

### Riesgo de sesgo
Modelo demasiado simple:
- falla tanto en entrenamiento como fuera de muestra.

### Riesgo de varianza
Modelo demasiado complejo:
- aprende ruido local,
- y degrada al salir del dataset de laboratorio.

### Regla de proyecto
Todo modelo debe evaluarse por:
- generalización,
- estabilidad,
- explicabilidad,
- coste de mantenimiento,
- y utilidad operativa.

## Métricas por tipo de problema

### Regresión
- MAE,
- RMSE,
- error por franja horaria,
- error por tamaño de grupo.

### Clasificación
- precision,
- recall,
- F1,
- matriz de confusión,
- tasa de falsos positivos.

### Probabilidades y scores
- calibración,
- distribución de score,
- utilidad operacional del umbral.

## Importancia de variables
Los modelos basados en árboles permiten estimar qué variables pesan más.

Eso es útil para:
- simplificar features,
- eliminar cálculos poco útiles,
- entender mejor el negocio,
- y explicar decisiones del sistema.

## Recomendaciones específicas para RestaurIA

### ETA de liberación
Empezar con:
- media histórica por franja y tamaño de grupo,
- luego Random Forest o Gradient Boosting.

Referencia específica:
- `docs/03_datos_y_ml/19_random_forest_para_eta_de_liberacion.md`

### Ocupación reforzada
Empezar con:
- reglas y señales visuales,
- luego un clasificador si hay suficientes ejemplos etiquetados.

Clasificadores candidatos:
- árbol de decisión,
- Random Forest,
- AdaBoost o Gradient Boosting si mejoran precisión sin perder explicabilidad operativa.

### Conteo de personas
No basarlo principalmente en Haar cascades.

Mejor enfoque:
- detección moderna de personas si se llega a usar,
- o combinación de señales visuales clásicas en el MVP temprano.

#### Sobre Haar cascades
Pueden tener valor histórico o servir en pruebas rápidas controladas, pero no deben considerarse la vía principal moderna del proyecto por:
- fragilidad ante ángulos y oclusiones,
- baja robustez en entorno real,
- y peor comportamiento frente a detectores actuales.

### Anomalías
Empezar con:
- reglas simples y percentiles,
- luego Isolation Forest si hay dataset suficiente.

### Segmentación no supervisada de comportamiento
Explorar solo si aparece una necesidad clara como:
- descubrir patrones de turnos,
- agrupar sesiones similares,
- o estudiar flujos de tráfico.

Herramientas razonables:
- K-Means,
- Gaussian Mixtures / EM.

## Qué entra en el MVP
- baseline estadístico,
- dataset estructurado para futuros modelos,
- persistencia de predicciones,
- capacidad de entrenar/regenerar modelos clásicos simples,
- y comparación explícita entre baseline y modelos candidatos.

## Qué se deja para después
- modelos más sofisticados,
- ensembles complejos,
- optimización intensiva de hiperparámetros,
- y cualquier despliegue de ML que no mejore una métrica real.

## Relación con la capa de decisión
El ML no debe decidir solo.

Debe alimentar:
- scores,
- ETA,
- riesgo,
- y recomendaciones,
que luego pasan por:
- reglas de negocio,
- umbrales,
- y supervisión humana.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/04_machine_learning.md`
- `docs/03_datos_y_ml/06_iea_y_motor_de_decision.md`
- `docs/07_ejecucion/03_plan_de_validacion.md`

## Conclusión
El ML en RestaurIA debe ser un amplificador de señales operativas, no un sustituto opaco de la lógica del sistema.

La estrategia correcta es:
- construir primero datos y eventos sólidos,
- usar modelos clásicos explicables,
- medir con rigor,
- escalar solo cuando el modelo mejore una decisión real,
- y preferir herramientas modernas de ML aunque la inspiración conceptual venga de OpenCV.
