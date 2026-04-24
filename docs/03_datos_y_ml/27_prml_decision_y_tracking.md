# PRML aplicado: decision y tracking ligero

## Proposito
Este documento aterriza ideas de *Pattern Recognition and Machine Learning* en RestaurIA sin convertir el MVP en un sistema pesado.

La aplicacion directa para el proyecto es:
- separar inferencia y decision,
- penalizar mas los errores peligrosos que los errores molestos,
- rechazar observaciones con incertidumbre alta,
- suavizar posiciones visuales con un modelo secuencial ligero,
- preparar features compactas y normalizadas para analitica posterior.

## Inferencia frente a decision
La camara produce senales imperfectas:
- conteo de personas,
- confianza de deteccion,
- bounding boxes,
- eventos derivados.

La capa de decision decide que hacer con esas senales:
- aceptar una transicion de estado,
- mantener el estado anterior,
- pedir revision humana,
- emitir una alerta operativa.

Esta separacion permite ajustar el comportamiento del restaurante sin reentrenar modelos.

## Matriz de perdida
No todos los errores cuestan lo mismo.

Ejemplo operativo:
- marcar una mesa ocupada como libre es grave,
- mantener una mesa libre como ocupada durante unos segundos es molesto, pero menos peligroso,
- pedir revision humana es aceptable cuando el sistema no tiene suficiente confianza.

Implementacion:
- `services/decision/policy.py`
- `LossMatrix`
- `DecisionPolicy`
- `DecisionPolicyConfig`
- `default_occupancy_loss_matrix()`

La politica calcula la perdida esperada de cada accion y elige la accion con menor coste. Si la confianza o el margen entre decisiones no es suficiente, devuelve una accion de rechazo como `request_review`.

## Opcion de rechazo en la FSM
La maquina de estados ya aplica una version practica de la opcion de rechazo.

Si una `TableObservation` llega con `confidence` menor que `min_transition_confidence`:
- se registra `people_counted`,
- se registra `low_confidence_observation`,
- no se inicia sesion,
- no se cierra sesion,
- no se cambia el estado operativo de la mesa.

Esto evita que un frame malo cierre una mesa, abra una sesion falsa o dispare ruido operativo.

Implementacion:
- `services/events/state_machine.py`
- `EventType.LOW_CONFIDENCE_OBSERVATION`

## Tracking ligero con Kalman
El detector visual puede producir cajas que vibran entre frames. El filtro de Kalman suaviza el centro de la caja usando un modelo de velocidad constante.

Ventajas:
- reduce parpadeos visuales,
- mantiene una prediccion durante un dropout breve,
- ayuda a estabilizar la asignacion persona-zona,
- no necesita GPU ni entrenamiento.

Implementacion:
- `services/vision/kalman.py`
- `ConstantVelocityKalmanFilter`
- `BoundingBoxKalmanSmoother`

Uso previsto:

```text
detector
  -> bbox raw
  -> NMS
  -> Kalman por track/persona
  -> bbox suavizada
  -> asignacion a zona
  -> TableObservation
```

## Que no se implementa todavia
Se pospone:
- HMM completo de fases de comida,
- Viterbi para reconstruccion diaria,
- EM/Baum-Welch,
- modelos de Markov de orden superior,
- inferencias sensibles como intencion de impago.

Ya queda preparada una capa ligera adicional:
- `services/features/preprocessing.py` para PCA, whitening, correlacion y estadisticos suficientes,
- `services/decision/committee.py` para combinar posteriores de modelos o reglas ligeras.

Motivo:
- aun no hay dataset real suficiente,
- el MVP debe demostrar primero ocupacion, eventos, sesiones, ETA y dashboard,
- el hardware objetivo es un ordenador normal con una camara.

## Criterio de evolucion
El siguiente paso coherente es conectar el pipeline real de camara:
1. OpenCV captura frames.
2. El detector produce bounding boxes.
3. NMS elimina duplicados.
4. Kalman estabiliza tracks.
5. El adaptador genera observaciones.
6. La FSM acepta o rechaza transiciones segun confianza.
7. La API muestra estado, eventos, predicciones y alertas.
