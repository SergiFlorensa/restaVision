# MLOps release gate y gobernanza de despliegue

## Objetivo
El índice de *Machine Learning Systems* aporta una visión de sistema que RestaurIA ya había empezado a cubrir: edge-first, feature store, monitorización, benchmarking, drift, validación y privacidad. El hueco práctico que faltaba era una compuerta de despliegue que impida promocionar un modelo solo porque "parece bueno" en métricas aisladas.

La pieza implantada convierte validación, latencia, calibración y controles de gobernanza en una decisión explícita: aprobado, aprobado con avisos o bloqueado.

## Lectura del índice

### Ya cubierto razonablemente
- **ML Systems / Edge ML**: el proyecto prioriza inferencia local, baja latencia y privacidad.
- **Data Engineering**: hay feature store, linaje y procesamiento consistente.
- **Efficient AI / Benchmarking AI**: hay medición de latencia y evaluación probabilística.
- **Robust AI**: existen drift, oclusiones, tracking y degradación controlada.
- **Responsible AI**: se evita identificación facial y se documentan límites.

### Hueco implantado
Los capítulos de **ML Operations**, **Benchmarking AI**, **Security & Privacy** y **Responsible AI** apuntan a una necesidad común: antes de desplegar un modelo hay que exigir controles mínimos de calidad, trazabilidad, privacidad y reversibilidad.

Eso se implementa en:

```text
services/governance/release_gate.py
```

## Qué comprueba la compuerta

La compuerta evalúa:

- accuracy mínima,
- F1 macro mínima para evitar esconder fallos en clases minoritarias,
- error de calibración máximo,
- latencia P95 máxima,
- tamaño máximo del modelo si se configura,
- test set bloqueado,
- linaje completo,
- revisión de privacidad,
- consistencia entre entrenamiento e inferencia,
- plan de rollback.

## Uso recomendado

```python
from services.governance import ModelReleaseCandidate, evaluate_model_release

candidate = ModelReleaseCandidate(
    model_id="restauria-yolo",
    model_version="2026.04.24",
    dataset_id="test-v1",
    accuracy=0.91,
    macro_f1=0.88,
    expected_calibration_error=0.04,
    p95_latency_ms=120,
    test_set_locked=True,
    lineage_complete=True,
    privacy_review_passed=True,
    training_serving_consistency_checked=True,
    rollback_plan_ready=True,
)

report = evaluate_model_release(candidate)
```

Si `report.status` es `blocked`, el modelo no debe entrar en el pipeline operativo.

## Por qué esto es más útil ahora que otra arquitectura
El sistema ya tiene suficientes piezas de visión e inferencia para un MVP. Añadir pruning, distillation o una red nueva todavía no aporta si no existe una regla formal para decidir cuándo un modelo está listo para operar.

Esta compuerta reduce deuda técnica porque fuerza a que cada despliegue tenga:

- métricas comparables,
- límites operativos,
- trazabilidad,
- privacidad revisada,
- rollback preparado.

## Cuándo cambiar de libro
Tras esta implementación, el libro sigue siendo útil si queremos profundizar en:

- seguridad adversarial,
- sostenibilidad energética,
- madurez MLOps,
- privacidad técnica avanzada.

Para avanzar el MVP de RestaurIA, probablemente ya conviene cambiar de libro si el siguiente objetivo es visión aplicada, UX/dashboard, producto o ingeniería de datos con Postgres/API.
