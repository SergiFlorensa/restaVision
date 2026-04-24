# Validación científica y métricas de ML

## Objetivo
El índice de *Understanding Deep Learning* muestra que RestaurIA no necesita añadir más arquitectura neuronal en este punto. Ya existen piezas para visión, tracking, confianza, explicabilidad y persistencia. El hueco relevante para el MVP es medir con rigor si esas piezas funcionan.

Este documento define la capa de evaluación científica implantada en `services/evaluation/`.

## Lectura del índice y decisión de implantación

### Ya cubierto en el proyecto
- **Capítulos 5 y 6, pérdidas y optimización**: se usa Softmax, NLL y selección de temperatura para confianza.
- **Capítulo 8, rendimiento**: existían ideas de validación, pero faltaba código reutilizable para métricas.
- **Capítulo 9, regularización**: ya hay criterios documentados para augmentation, early stopping y weight decay.
- **Capítulo 10, CNNs**: el sistema mantiene YOLO como detector desacoplado.
- **Capítulo 11, residual y BatchNorm**: se documenta como futuro solo si se añaden redes propias.
- **Capítulo 21, ética**: ya se evita reconocimiento facial y se añade trazabilidad de decisiones.

### No conviene implantar aún
- **Transformers de imagen**: coste alto para vídeo local en portátil.
- **GANs, flows, VAEs y difusión**: útiles en investigación, pero no necesarios para el MVP de una cámara y una mesa.
- **Reinforcement learning**: no hay entorno simulado ni política de actuación automática que lo justifique.
- **GNNs completas**: la sala puede modelarse como grafo más adelante, pero no hace falta entrenar una red de grafos ahora.

### Gap implantado
El punto que faltaba era una capa de evaluación que permita:

- construir matriz de confusión,
- calcular precision, recall, F1 y accuracy,
- evaluar predicciones probabilísticas,
- calcular negative log-likelihood,
- calcular Brier score,
- medir calibración con expected calibration error,
- barrer umbrales de confianza para elegir cuándo María debe actuar o pedir revisión.

## Módulo implementado
Archivo principal:

```text
services/evaluation/metrics.py
```

Funciones principales:

- `confusion_matrix`: resume errores por clase.
- `classification_report`: genera métricas por clase y agregadas.
- `evaluate_probability_predictions`: evalúa probabilidades con accuracy, NLL, Brier y calibración.
- `expected_calibration_error`: mide si la confianza del modelo corresponde con su tasa real de acierto.
- `sweep_confidence_thresholds`: permite elegir umbrales operativos comparando cobertura frente a precisión.

## Uso recomendado para el TFG

1. Separar datos en train, validation y test.
2. Entrenar o ajustar el detector solo con train.
3. Elegir temperatura Softmax y umbral de confianza solo con validation.
4. Reservar test para la medición final de la memoria.
5. Reportar matriz de confusión, F1 macro, NLL, Brier y ECE.

Ejemplo:

```python
from services.evaluation import evaluate_probability_predictions, sweep_confidence_thresholds

labels = ("ready", "occupied", "dirty")
report = evaluate_probability_predictions(labels, y_true, probability_rows, bins=10)

thresholds = sweep_confidence_thresholds(
    labels,
    y_true,
    probability_rows,
    thresholds=(0.60, 0.70, 0.80, 0.90),
)
```

## Interpretación operativa

- **F1 macro bajo**: una clase minoritaria, como `dirty`, se está ignorando.
- **NLL alto**: el modelo asigna poca probabilidad a la clase correcta.
- **Brier alto**: las probabilidades son malas aunque a veces acierte la clase.
- **ECE alto**: el modelo está mal calibrado; no conviene usar sus probabilidades como umbrales.
- **Cobertura baja en threshold sweep**: el sistema rechaza demasiados frames y puede quedarse sin eventos útiles.

## Criterio de aceptación
Antes de desplegar un modelo ajustado al local:

- el validation set debe tener ejemplos reales sin augmentation,
- el test set no debe usarse para elegir hiperparámetros,
- el umbral de confianza debe elegirse por barrido medido,
- toda métrica debe guardarse junto a versión de modelo, fecha y dataset,
- cualquier mejora debe compararse contra el baseline anterior.

Esta capa es más valiosa ahora que implementar arquitecturas avanzadas porque convierte las salidas visuales en evidencia medible para el TFG y para decisiones operativas reales.
