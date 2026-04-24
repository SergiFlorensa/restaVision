# Modelos probabilísticos y suavizado temporal con Viterbi

## Objetivo
El índice de *Computer Vision: Models, Learning and Inference* aporta una idea muy útil para RestaurIA: tratar las salidas visuales como evidencias probabilísticas y conectar decisiones locales mediante modelos temporales.

La implementación elegida es pequeña y viable: inferencia MAP en cadenas mediante Viterbi y filtrado online tipo HMM para suavizar estados de mesa.

## Lectura del índice

### Ya cubierto en el proyecto
- **Probabilidad y Bayes**: ya existen política bayesiana, comité de posteriors y filtro de confianza.
- **Distribución normal y modelos gaussianos**: ya existen anomalías multivariantes y drift.
- **Transformaciones geométricas**: ya existen calibración, homografías y rectificación de mesa.
- **Preprocesado**: ya existen histograma, Sobel, motion gate y slicing/ROI.
- **Temporal models / Kalman**: ya existe filtro de Kalman y tracking Lucas-Kanade.

### Gap implantado
Faltaba una forma genérica de conectar observaciones locales en una secuencia temporal y obtener tanto la trayectoria de estados más probable como la creencia actual por estado.

Eso se implementa en:

```text
services/decision/sequence.py
services/decision/observation_model.py
services/decision/sequence_config.py
```

## Qué resuelve Viterbi
YOLO o la lógica de conteo pueden producir saltos espurios:

- `ocupada → libre → ocupada` por una oclusión,
- `mesa finalizando → ocupada` por una detección inestable,
- `vacía → ocupada` por una falsa persona en el borde de la ROI.

Viterbi permite combinar:

- probabilidad local del estado en cada frame o ventana,
- probabilidad de transición entre estados,
- camino global más probable.

## Traducción matemática a código
Modelo:

- estados: `ready`, `occupied`, `finalizing`, `pending_cleaning`,
- emisiones: probabilidad observada de cada estado en cada instante,
- transiciones: probabilidad de pasar de un estado a otro.

Inferencia:

```text
score[t, state] =
    log(emission[t, state]) +
    max_prev(score[t-1, prev] + log(transition[prev, state]))
```

El resultado es la secuencia MAP de estados.

## Forward filtering para tiempo real
Viterbi es útil para reconstruir el mejor camino en una ventana. Para operación en vivo interesa además actualizar la probabilidad actual de cada estado con cada observación.

La actualización online es:

```text
prior_t(state) = sum_prev belief_{t-1}(prev) * transition(prev, state)
posterior_t(state) = normalize(prior_t(state) * likelihood_t(state))
```

Esto permite mostrar en dashboard:

- `occupied: 0.82`,
- `ready: 0.10`,
- `finalizing: 0.05`,
- `pending_cleaning: 0.03`.

## Modelo de observación
El módulo `services/decision/observation_model.py` convierte una `TableObservation` en likelihoods de estado:

- si `people_count == 0`, favorece `ready`,
- si `people_count > 0`, favorece `occupied`,
- si la confianza visual es baja, mezcla con una distribución uniforme para expresar incertidumbre.

No sustituye la calibración real. Es un baseline interpretable y configurable.

## Configuración externa del modelo temporal
El módulo `services/decision/sequence_config.py` permite cargar el modelo de cadena de Markov desde configuración externa.

JSON está soportado sin dependencias adicionales. YAML queda soportado solo si el entorno tiene `PyYAML`; si no, el loader falla de forma explícita y recomienda usar JSON.

Ejemplo JSON:

```json
{
  "states": ["ready", "occupied", "finalizing", "pending_cleaning"],
  "start_probabilities": {
    "ready": 0.70,
    "occupied": 0.20,
    "finalizing": 0.05,
    "pending_cleaning": 0.05
  },
  "transition_probabilities": {
    "ready": {
      "ready": 0.92,
      "occupied": 0.08,
      "finalizing": 0.0,
      "pending_cleaning": 0.0
    },
    "occupied": {
      "ready": 0.02,
      "occupied": 0.90,
      "finalizing": 0.07,
      "pending_cleaning": 0.01
    },
    "finalizing": {
      "ready": 0.01,
      "occupied": 0.25,
      "finalizing": 0.68,
      "pending_cleaning": 0.06
    },
    "pending_cleaning": {
      "ready": 0.20,
      "occupied": 0.0,
      "finalizing": 0.0,
      "pending_cleaning": 0.80
    }
  }
}
```

Uso:

```python
from services.decision import load_markov_chain_model

model = load_markov_chain_model("config/table_state_model.json")
```

Esto permite ajustar el comportamiento por restaurante sin cambiar código.

## Uso recomendado

```python
from services.decision import MarkovChainModel, ViterbiDecoder

model = MarkovChainModel(
    states=("ready", "occupied"),
    transition_probabilities={
        "ready": {"ready": 0.90, "occupied": 0.10},
        "occupied": {"ready": 0.05, "occupied": 0.95},
    },
)

decoder = ViterbiDecoder(model)
result = decoder.decode(observation_posteriors)
```

## Encaje en RestaurIA
No se conecta todavía automáticamente a `TableStateMachine` para no cambiar el comportamiento operativo sin calibración real.

Uso correcto:

1. acumular una ventana corta de posteriors por mesa,
2. ejecutar Viterbi,
3. usar el último estado decodificado como señal suavizada,
4. comparar contra el estado actual antes de emitir eventos.

Uso online:

1. convertir cada `TableObservation` en likelihood,
2. pasarla por `ForwardFilter.update`,
3. usar `selected_state` y `confidence` como estado probabilístico actual,
4. mantener el `TableStateMachine` como responsable final de eventos hasta calibrar el modelo.

## Coste computacional
Complejidad aproximada:

```text
O(T * S^2)
```

donde `T` es la longitud de la ventana y `S` el número de estados.

Para 4 estados y ventanas de 5-20 observaciones es trivial en portátil básico.

## Qué no conviene aplicar ahora

- **MRF/grid models**: demasiado pesados para el MVP; útiles para segmentación densa, no para mesa única.
- **Graph cuts**: potente, pero excesivo para estados operativos.
- **EM/GMM completo**: útil con histórico real amplio; por ahora basta con Gaussian/Mahalanobis.
- **Particle filters**: fase posterior si Kalman deja de ser suficiente.
- **Identidad/estilo**: no encaja con privacidad; evitar reidentificación personal.

## Criterio de adopción
Forward filtering puede usarse antes que Viterbi porque trabaja online con una sola observación cada vez. Viterbi queda para ventanas cortas y validación posterior de trayectorias.
