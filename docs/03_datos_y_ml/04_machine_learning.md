# Capa de Machine Learning

## Objetivo
Aprender patrones y predecir eventos o tiempos relevantes.

## Problemas ML principales
### 1. Predicción de duración total
¿Cuánto suele durar una sesión de una mesa?

### 2. Predicción de tiempo restante
Dada la situación actual, ¿cuánto falta para que termine?

### 3. Predicción de cola / espera
Si entra un grupo, ¿cuánto tiempo realista debería esperar?

### 4. Detección de anomalías
¿Qué mesas o sesiones se comportan de forma extraña?

## Variables candidatas
- personas iniciales,
- ocupación actual,
- tiempo transcurrido,
- franja horaria,
- día,
- festivo,
- estado de mesa,
- número de cambios de estado,
- densidad global del local.

## Modelos iniciales recomendados
- baseline estadístico,
- regresión,
- Random Forest,
- XGBoost / LightGBM,
- Isolation Forest para anomalías.

## Métricas
- MAE y RMSE para tiempos,
- Precision / Recall / F1 para eventos o riesgos,
- calibration si se devuelven probabilidades,
- tasa de falsos positivos en alertas.

## Recomendación
Antes de usar deep learning temporal, construir baselines clásicos fuertes y explicables.

## Estado aplicado en MVP
Ya existe una primera pieza de anomalias operativas en `services/alerts/anomaly.py`.

Caracteristicas:
- usa solo estadistica descriptiva sobre duracion de sesiones,
- exige historico minimo antes de alertar,
- expone evidencia numerica en `GET /api/v1/alerts`,
- no introduce dependencias pesadas,
- no automatiza acusaciones de impago ni inferencias sensibles.

Tambien se aplica teoria de decision de forma ligera:
- `services/decision/policy.py` define matriz de perdida y perdida esperada,
- la FSM usa opcion de rechazo para observaciones de baja confianza,
- `services/vision/kalman.py` prepara tracking secuencial ligero para bounding boxes.
- `services/features/preprocessing.py` aporta PCA, whitening, correlacion y estadisticos suficientes.
- `services/decision/committee.py` combina probabilidades de fuentes ligeras antes de decidir.
- `services/maria/orchestrator.py` decide cuándo invocar analisis multimodal puntual en lugar de procesar cada frame.

## Documento complementario
- `docs/03_datos_y_ml/18_ml_clasico_y_modelado_predictivo.md`
- `docs/03_datos_y_ml/26_anomalias_operativas_estadisticas.md`
- `docs/03_datos_y_ml/27_prml_decision_y_tracking.md`
- `docs/03_datos_y_ml/28_pca_whitening_y_comites.md`
- `docs/04_software_y_devops/13_maria_flujo_doble_velocidad.md`
