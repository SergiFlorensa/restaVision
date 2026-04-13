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
