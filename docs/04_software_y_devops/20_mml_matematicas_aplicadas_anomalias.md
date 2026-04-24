# Matemáticas aplicadas a anomalías operativas

## Objetivo
El índice de *Mathematics for Machine Learning* aporta fundamentos matemáticos, no recetas de arquitectura de software. Para RestaurIA, la mayor parte ya estaba cubierta de forma práctica: homografías, SVD/PCA, estadística online, calibración probabilística, métricas y decisión bayesiana.

La pieza pequeña que sí añade valor es usar geometría, probabilidad gaussiana y álgebra matricial para detectar anomalías multivariantes en señales operativas de mesa.

## Lectura del índice

### Fundamentos ya aplicados
- **Álgebra lineal**: matrices, transformaciones, homografías, Kalman y PCA.
- **Geometría analítica**: distancias, proyecciones y zonas métricas.
- **Descomposiciones matriciales**: SVD para PCA y homografía estable.
- **Probabilidad**: confianza, drift, distribución de scores y validación.
- **Optimización**: relevante para entrenamiento, pero no conviene implementar desde cero.

### Fundamento implantado ahora
Se implementa un perfil gaussiano multivariante:

```text
services/alerts/multivariate.py
```

El perfil aprende:

- media de las señales normales,
- matriz de covarianza,
- matriz de precisión mediante pseudoinversa regularizada,
- distancia de Mahalanobis para puntuar desviaciones.

## Por qué Mahalanobis y no solo z-score
El z-score univariante detecta si una señal aislada está fuera de rango. La distancia de Mahalanobis detecta combinaciones raras teniendo en cuenta correlaciones.

Ejemplo operativo:

- duración alta con cuatro personas puede ser normal,
- duración alta con una persona y mucho movimiento puede ser raro,
- movimiento alto con mesa ocupada puede ser normal,
- movimiento alto con mesa supuestamente vacía puede indicar fallo de detección o limpieza.

## Traducción a código

Entradas:

- `duration_min`,
- `people_count`,
- `motion`,
- `edge_density`,
- `confidence`,
- cualquier feature numérica estable del pipeline.

Salida:

- `is_anomaly`,
- distancia de Mahalanobis al cuadrado,
- umbral configurado,
- z-scores por feature para explicar la alerta.

Uso:

```python
from services.alerts import MultivariateGaussianAnomalyDetector, fit_multivariate_gaussian_profile

profile = fit_multivariate_gaussian_profile(history, min_samples=20)
detector = MultivariateGaussianAnomalyDetector(profile)
result = detector.score(current_features)
```

## Coste computacional

- Entrenamiento del perfil: coste cúbico en número de features por la pseudoinversa, pero se hace offline o poco frecuente.
- Scoring por frame/evento: coste cuadrático en número de features.
- Para 3-10 features operativas es apto para portátil básico.

## Encaje en RestaurIA
Este módulo no sustituye a YOLO ni al state machine. Es una capa de alerta sobre señales ya agregadas.

Encaja en:

- `services/alerts/` para anomalías,
- `services/features/` como fuente de features,
- `services/maria/` para explicar alertas suaves,
- dashboard como tarjeta de “comportamiento fuera de patrón”.

## Qué no conviene implementar ahora

- **GMM/EM completo**: útil si hay varios patrones normales, pero necesita más datos y ajuste.
- **SVM**: no aporta mucho sin dataset etiquetado de anomalías.
- **Optimización custom**: usar NumPy/scikit/Ultralytics cuando toque; no escribir solvers propios.
- **Derivadas/backprop**: ya lo resuelven PyTorch/Ultralytics.

## Criterio de uso
Usarlo solo sobre datos agregados por evento o ventana temporal, no sobre cada píxel ni cada frame crudo.

Parámetros iniciales:

- `min_samples >= 20` en entorno real,
- `max_mahalanobis_squared = 9.0` como umbral inicial conservador,
- `regularization = 1e-6` para evitar problemas con covarianzas singulares.

Antes de tratar una alerta como crítica, debe combinarse con evidencia visual, confianza del detector y estado de mesa.
