# PCA, whitening y comites ligeros

## Proposito
Este documento aplica el bloque final de PRML al contexto realista de RestaurIA: ahorrar CPU, reducir redundancia y combinar senales ligeras sin exigir GPU ni entrenamientos complejos.

El objetivo no es entrenar modelos avanzados todavia, sino dejar preparadas utilidades matematicas fiables para cuando existan datos reales.

## Que se implementa ahora
Se anaden tres piezas:
- PCA para reducir dimensionalidad de matrices de features,
- whitening para normalizar features correlacionadas,
- comite ponderado para combinar probabilidades de modelos o reglas ligeras.

Codigo:
- `services/features/preprocessing.py`
- `services/decision/committee.py`

Tests:
- `tests/test_feature_preprocessing.py`
- `tests/test_committee.py`

## PCA
PCA proyecta datos de alta dimension a un subespacio menor manteniendo la mayor varianza posible.

Uso futuro en RestaurIA:
- comprimir features derivadas de detecciones,
- analizar vectores de comportamiento por sesion,
- reducir columnas redundantes antes de entrenar ETA,
- estudiar si hay dimensiones operativas dominantes.

No debe usarse todavia sobre pixels crudos de video en tiempo real. Para el MVP es mas sensato usarlo sobre features pequenas:
- duracion de sesion,
- conteos por ventana,
- ratios de ocupacion,
- confianza media del detector,
- numero de cambios de estado,
- variables de franja horaria.

## Whitening
Whitening transforma features para que queden centradas y descorrelacionadas en el espacio PCA.

Valor:
- facilita modelos lineales,
- reduce problemas por escalas diferentes,
- ayuda a comparar variables como segundos, conteos y probabilidades.

Limitacion:
- debe ajustarse con datos representativos,
- si se mueve la camara o cambia la operativa, conviene recalibrar.

## Estadisticos suficientes
`RunningFeatureStats` permite acumular:
- conteo,
- media,
- varianza poblacional,
- varianza muestral.

Esto evita guardar cada observacion de bajo nivel cuando solo se necesitan agregados para analitica o entrenamiento posterior.

## Matriz de correlacion
`correlation_matrix()` permite detectar variables redundantes.

Uso:
- ver si dos features aportan casi lo mismo,
- simplificar modelos,
- reducir ruido antes de entrenar ETA o alertas.

La implementacion maneja columnas constantes sin generar `NaN`.

## Comite ponderado
`WeightedPosteriorCommittee` combina probabilidades de varias fuentes:
- regla geometrica,
- suavizado temporal,
- detector visual rapido,
- predictor historico.

El resultado es una distribucion posterior comun que puede alimentar `DecisionPolicy`.

Ejemplo conceptual:

```text
geometria:        ready=0.70 occupied=0.30
temporal:         ready=0.40 occupied=0.60
comite ponderado: ready=0.55 occupied=0.45
decision policy:  mark_occupied o request_review segun perdida y confianza
```

## Que se pospone
Se pospone:
- AdaBoost entrenado,
- SVM/RVM,
- kernels RBF,
- ARD,
- EM para datos faltantes,
- PCA sobre imagenes completas.

Motivo:
- aun no hay dataset propio suficiente,
- el MVP debe correr en un ordenador normal,
- primero hay que medir ocupacion, latencia y estabilidad de estados con camara real.

## Criterio profesional
Estas piezas son infraestructura matematica de bajo coste.

Son utiles si:
- reducen columnas,
- hacen los datos mas estables,
- facilitan tests reproducibles,
- explican mejor las decisiones.

No deben convertirse en una excusa para aplazar el pipeline principal de camara.
