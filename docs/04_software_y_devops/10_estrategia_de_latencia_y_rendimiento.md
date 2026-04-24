# Estrategia de latencia y rendimiento

## Propósito
Definir cómo minimizar la latencia de RestaurIA sin degradar la utilidad operativa ni convertir el sistema en una base técnica opaca o difícil de mantener.

Este documento se centra en:
- reducción de coste por frame,
- optimización del cálculo de ETA,
- uso eficiente de ROIs,
- paralelización razonable,
- y decisiones de rendimiento compatibles con el MVP y con un futuro piloto real.

## Decisión técnica principal
La latencia debe optimizarse por capas, en este orden:
1. reducir trabajo innecesario,
2. reducir complejidad de datos y features,
3. mejorar arquitectura de procesamiento,
4. paralelizar donde tenga sentido,
5. y solo después entrar en optimización más agresiva o dependiente de hardware.

En otras palabras:
- primero menos trabajo,
- luego trabajo más barato,
- y solo al final más potencia o más complejidad.

## Principio rector
En RestaurIA, la latencia útil no significa “calcular lo más rápido posible a cualquier coste”, sino:
- responder en tiempo operativo,
- mantener estabilidad,
- preservar explicabilidad,
- y no sobrecargar el hardware con trabajo irrelevante.

## 1. Optimización por reducción de variables

### Qué problema resuelve
Si el modelo de ETA usa demasiadas features:
- aumenta coste de preparación,
- aumenta complejidad,
- empeora mantenibilidad,
- y puede introducir ruido innecesario.

### Estrategia recomendada
Reducir las variables a las que realmente aportan señal.

### Aplicación práctica en el proyecto
Para modelos modernos como `RandomForestRegressor`, usar:
- `feature_importances_`,
- análisis de ablación,
- comparación con baseline reducido,
- y revisión de negocio.

### Regla de adopción
Una feature se mantiene si:
- mejora métricas,
- está disponible de forma estable en producción,
- y su coste de cálculo compensa su valor.

### Qué no hacer
No mantener features porque “quizá algún día sirvan”.
Toda feature en producción es una deuda de cálculo y mantenimiento.

## 2. Optimización por ROIs y vistas locales

### Regla básica
Nunca procesar el frame completo si la decisión depende de una mesa concreta.

### Patrón recomendado
Por cada frame:
- cargar zonas activas,
- extraer vistas locales,
- aplicar pipeline por ROI,
- y producir observaciones por mesa.

### Escalado a múltiples mesas
En la API clásica esto se explicaba con múltiples encabezados y `widthStep`.
En RestaurIA, la adaptación moderna es:
- vistas `numpy` sobre el mismo frame,
- slices por zona,
- máscaras por mesa,
- y paquetes de observaciones locales sin copias innecesarias.

### Beneficios
- menos CPU,
- menos ruido,
- menos falsos positivos,
- menor latencia por frame.

## 3. Optimización por preprocesado eficiente

### Reducción de resolución
Usar resolución menor cuando:
- el hardware sea modesto,
- la señal útil siga presente,
- y la mejora de latencia sea medible.

Herramientas razonables:
- `cv2.resize`
- `cv2.pyrDown`

### Imágenes integrales
Tienen valor cuando hace falta calcular sumas rápidas en muchas subregiones rectangulares.

Aplicación útil:
- densidad de primer plano por mesa,
- energía de movimiento,
- señales rápidas por ROI.

### Regla práctica
Las imágenes integrales merecen entrar si:
- hay muchas mesas,
- muchas regiones rectangulares,
- y el coste agregado del cómputo por ROI empieza a pesar de verdad.

## 4. Optimización del cálculo de ETA

### En qué parte está la latencia real
El tiempo de ETA no suele estar dominado por el árbol o bosque en sí, sino por:
- preparación de features,
- lectura de estado,
- y sincronización con el resto del pipeline.

### Estrategias recomendadas
- recalcular ETA solo cuando cambie algo relevante,
- no predecir en cada frame si no aporta valor,
- usar snapshots temporales razonables,
- cachear features lentas de calcular,
- y reducir el número de predicciones innecesarias.

### Frecuencia recomendada
El ETA puede recalcularse:
- por evento relevante,
- por ventana temporal discreta,
- o por cambio de estado,
en vez de hacerlo para cada frame de vídeo.

## 5. Paralelización

### Regla general
La paralelización sí puede ayudar, pero debe entrar después de haber reducido el trabajo inútil.

### Dónde tiene más sentido
- procesado independiente por mesa,
- procesado independiente por cámara,
- cálculo batch de observaciones,
- o inferencia de ETA por lote.

### En el proyecto
La forma más segura de introducir paralelización es:
- a nivel de pipeline o worker,
- no asumiendo a ciegas que cualquier método de predicción es thread-safe en cualquier implementación.

### Adaptación al stack moderno
En vez de apoyarse en afirmaciones de la API antigua, en RestaurIA conviene:
- validar explícitamente concurrencia del runtime elegido,
- usar `n_jobs` cuando aplique,
- o paralelizar a nivel de proceso/tarea y no dentro del objeto sin medir.

## 6. Optimización específica de modelos

### Para Random Forest
El coste en predicción suele ser razonable, pero puede crecer por:
- demasiados árboles,
- árboles muy profundos,
- muchas features inútiles.

### Estrategia recomendada
- entrenar con un número razonable de árboles,
- medir latencia de inferencia real,
- recortar features irrelevantes,
- y evitar optimización teórica sin benchmark real.

### Sobre criterios de parada
En el stack moderno del proyecto, esto se traduce más en:
- selección de hiperparámetros razonables,
- validación fuera de muestra,
- y comparación contra baseline,
que en reproducir literalmente `CvTermCriteria`.

## 7. Aceleración de OpenCV y hardware

### IPP
Si la build de OpenCV la soporta, puede acelerar operaciones base de visión.

### Regla práctica
No debe asumirse a ciegas:
- hay que comprobar cómo está construida la instalación real de OpenCV,
- y medir si las operaciones críticas se benefician materialmente.

### Relación con el proyecto
Esto es más relevante en:
- piloto real,
- varias mesas,
- o varias cámaras,
que en el laboratorio doméstico inicial.

## 8. Qué optimizar primero en RestaurIA

### Orden recomendado
1. ROI por mesa
2. menor resolución cuando proceda
3. menos features para ETA
4. menos frecuencia de predicción
5. cacheo de señales costosas
6. imágenes integrales si el patrón de uso lo justifica
7. paralelización por zona/cámara
8. optimización dependiente de hardware

## 9. Qué no conviene hacer
- predecir ETA en cada frame,
- usar el frame completo para decisiones locales,
- introducir paralelización compleja sin profiling,
- aumentar complejidad del modelo para ganar décimas irrelevantes,
- u optimizar entrenamiento cuando el cuello real está en visión o en extracción de features.

## 10. Métricas de rendimiento que deben medirse

### Por capa
- tiempo de captura,
- tiempo de preprocesado por ROI,
- tiempo de segmentación,
- tiempo de extracción de señales,
- tiempo de inferencia ETA,
- tiempo total por frame o por ciclo.

### De sistema
- FPS efectivo,
- latencia end-to-end,
- uso de CPU,
- uso de memoria,
- estabilidad a largo plazo,
- y coste por número de mesas activas.

## 11. Relación con el ETA
El ETA no necesita actualización instantánea a 30 FPS.

Lo que necesita es:
- consistencia,
- frecuencia suficiente para apoyar decisiones,
- y coste bajo comparado con el pipeline visual.

Principio operativo:
- mejor un ETA estable cada pocos segundos o por evento relevante,
- que un ETA que cambie frenéticamente en cada frame.

## 12. Recomendación arquitectónica final
Separar claramente:
- frecuencia de captura,
- frecuencia de observación,
- frecuencia de cambio de estado,
- y frecuencia de predicción de ETA.

No tienen por qué ser la misma.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/18_ml_clasico_y_modelado_predictivo.md`
- `docs/03_datos_y_ml/19_random_forest_para_eta_de_liberacion.md`
- `docs/04_software_y_devops/09_video_to_observation_adapter.md`
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`

## Conclusión
La latencia de RestaurIA no se gana con un único truco, sino con una cadena de decisiones correctas:
- menos datos inútiles,
- menos trabajo por mesa,
- menos predicciones innecesarias,
- y una arquitectura que desacople bien visión, observación y ETA.

Si esto se hace bien, el sistema podrá ofrecer tiempos de respuesta útiles incluso en hardware modesto, sin sacrificar claridad ni capacidad de evolución.
