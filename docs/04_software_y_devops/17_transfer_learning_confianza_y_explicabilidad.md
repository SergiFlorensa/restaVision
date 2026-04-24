# Transfer learning, confianza y explicabilidad ligera

## Objetivo
Este documento aterriza las ideas más útiles de aprendizaje profundo para el MVP de RestaurIA sin romper las restricciones del proyecto: ejecución local, portátil básico, una cámara, una mesa y decisiones operativas explicables.

La prioridad no es añadir modelos más grandes. La prioridad es controlar cuándo una salida visual merece convertirse en evento de negocio.

## Decisión principal
RestaurIA debe separar tres capas:

1. **Entrenamiento y adaptación**: fine-tuning de YOLO con datos del local, augmentation y validación.
2. **Inferencia operativa**: ejecución local del detector ya entrenado.
3. **Gobernanza de decisión**: filtro de confianza, rechazo explícito y trazas de explicabilidad.

Esta separación evita que una probabilidad baja o una salida ambigua escriba eventos falsos en la capa de persistencia.

## Filtro de confianza Softmax
El módulo `services/decision/confidence.py` añade una compuerta previa a la política de decisión:

- convierte logits en probabilidades con Softmax estable,
- normaliza distribuciones ya calculadas por otros modelos,
- mide confianza máxima,
- mide entropía normalizada,
- rechaza salidas ambiguas con una etiqueta explícita de revisión.

Uso recomendado:

```python
from services.decision.confidence import ConfidenceGate, ConfidenceGateConfig

gate = ConfidenceGate(ConfidenceGateConfig(min_confidence=0.85, max_entropy_ratio=0.90))
result = gate.evaluate_logits(("ready", "occupied", "dirty"), logits)

if result.accepted:
    action = result.label
else:
    action = "request_review"
```

Este filtro no sustituye a la matriz de pérdidas de `DecisionPolicy`. La complementa: primero se descartan salidas visuales débiles; después se decide con coste explícito.

## Calibración de temperatura
El mismo módulo incluye `select_temperature_by_nll` para elegir una temperatura de Softmax usando el conjunto de validación.

La temperatura no mejora el detector por sí misma. Sirve para que las probabilidades sean menos arrogantes y más útiles como umbrales operativos.

Regla práctica:

- ajustar temperatura solo con validación,
- no tocar el test set,
- registrar la temperatura usada junto al modelo desplegado.

## Explicabilidad ligera por oclusión
El módulo `services/vision/explainability.py` implementa una alternativa ligera a LIME basada en sensibilidad por oclusión de parches.

Funcionamiento:

1. calcula el score base del modelo para una imagen o ROI,
2. tapa parches pequeños,
3. vuelve a calcular el score,
4. asigna mayor importancia a los parches cuya oclusión reduce más la puntuación.

Esto permite guardar evidencia visual cuando María genera una alerta dudosa, sin añadir dependencias pesadas ni ejecutar modelos secundarios.

Uso recomendado:

```python
from services.vision.explainability import PatchOcclusionConfig, occlusion_sensitivity

explanation = occlusion_sensitivity(
    table_roi,
    score_fn,
    table_id="table_01",
    score_name="dirty_table",
    config=PatchOcclusionConfig(patch_size=16, stride=8),
)

important_patches = explanation.top_patches(limit=3)
```

## Qué no se implementa aún

### Bloques residuales y BatchNorm custom
No son prioritarios en el MVP porque YOLO ya incorpora arquitectura optimizada. Solo tendría sentido implementarlos si RestaurIA añade una red propia para estados de mesa.

### Pruning
La poda requiere un modelo entrenado, evaluación antes/después y una librería de despliegue que aproveche pesos dispersos. Implementarla antes de tener un baseline medido sería optimización prematura.

### Knowledge distillation
La destilación es útil si existe un modelo maestro entrenado y un dataset estable. En el MVP todavía no hay volumen ni madurez suficiente para justificarla.

### Vision Transformers
Se descartan para el MVP por coste computacional y memoria. La arquitectura CNN/YOLO sigue siendo más adecuada para vídeo local en 720p.

## Criterios de aceptación
Un despliegue de IA visual se considera gobernado si cumple:

- toda salida de modelo pasa por un filtro de confianza,
- las probabilidades se calibran con validation set, no con test set,
- las alertas críticas tienen traza de score, umbral y razón de aceptación/rechazo,
- las explicaciones se calculan bajo demanda, no en todos los frames,
- el test set permanece aislado para la memoria del TFG.

## Encaje con el MVP
Esta implementación refuerza el MVP sin ampliar alcance:

- reduce falsos eventos,
- mejora la trazabilidad para la memoria,
- mantiene el pipeline local-first,
- evita nuevas dependencias,
- deja preparada la futura fase de fine-tuning real.
