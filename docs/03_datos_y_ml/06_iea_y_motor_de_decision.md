# Capa inteligente de explotacion y apoyo a decision

## Papel de la capa IEA
En RestaurIA, la capa IEA no debe limitarse a clasificar estados. Su funcion es convertir estado operativo en decisiones utiles para el responsable de sala.

Debe:
- interpretar el estado de mesas, cola y zonas,
- priorizar alertas,
- estimar presion operativa,
- recomendar la siguiente mejor accion,
- explicar por que sugiere algo,
- registrar si la accion fue aceptada y si funciono.

## Principio rector

```text
Observacion -> evento -> interpretacion -> prioridad -> recomendacion -> feedback
```

Si una salida no conduce a una accion clara, no debe molestar durante el servicio.

## Componentes recomendados

### Maquina de estados de mesa
Estados base:
- `ready`,
- `occupied`,
- `eating`,
- `finalizing`,
- `pending_cleaning`,
- `blocked`,
- `needs_attention`,
- `unknown`.

### Restaurant Pressure Index
Calcula presion operativa del restaurante.

Variables iniciales:
- ocupacion total,
- grupos en cola,
- promesas de espera en riesgo,
- mesas finalizando,
- mesas pendientes de limpieza,
- alertas P1,
- tiempo medio de cola.

Salida:
- puntuacion 0-100,
- modo recomendado: `normal`, `busy`, `critical_service`.

### Table Opportunity Score
Puntua cada mesa segun oportunidad operativa.

Factores:
- compatibilidad con grupos en cola,
- estado `finalizing` o `pending_cleaning`,
- capacidad de mesa,
- tiempo de sesion,
- ETA baseline,
- presion actual.

### Promise Engine
Calcula que espera comunicar a un grupo.

Debe evitar promesas irreales y actualizar la recomendacion si cambia el estado de sala.

Salida minima:
- rango de espera,
- mesa candidata,
- confianza,
- riesgo de incumplimiento,
- mensaje recomendado.

### Next Best Action
Genera recomendaciones concretas.

Ejemplos:
- preparar Mesa 12 para grupo de 4,
- actualizar espera del grupo de entrada,
- revisar Mesa 05 por posible primera atencion tardia,
- no sentar grupo de 2 en mesa de 6 si hay grupo grande esperando,
- enviar apoyo a zona centro.

### Decision Explainer
Toda recomendacion debe poder justificar:
- variables clave,
- eventos recientes,
- prioridad,
- nivel de confianza,
- caducidad.

### Feedback Recorder
Registra:
- recomendacion aceptada,
- recomendacion ignorada,
- recomendacion incorrecta,
- resultado observado,
- comentario manual opcional.

Este feedback es necesario para pasar de reglas baseline a aprendizaje por restaurante.

## Objeto `DecisionRecommendation`

```json
{
  "decision_id": "dec_0001",
  "mode": "critical_service",
  "priority": "P1",
  "question": "Y ahora que hago?",
  "answer": "Preparar Mesa 12 para grupo de 4",
  "table_id": "mesa_12",
  "queue_group_id": "queue_group_04",
  "eta_minutes": 9,
  "confidence": 0.78,
  "impact": "reduce_wait_time",
  "reason": [
    "mesa compatible",
    "mesa finalizando",
    "cola activa",
    "tiempo superior a la media"
  ],
  "expires_in_seconds": 180
}
```

## Prioridades de alerta

### P1 - accion inmediata
- cliente esperando demasiado,
- promesa de espera en riesgo,
- mesa lista sin limpiar con cola activa,
- mesa desatendida,
- mesa compatible proxima a liberarse.

### P2 - revisar pronto
- mesa superando media,
- mesa finalizando,
- zona con baja cobertura,
- servicio incompleto.

### P3 - solo historico
- deteccion menor,
- cambio visual sin accion,
- movimiento normal.

## Regla clave
El sistema no acusa ni decide por si solo sobre personas. Recomienda acciones operativas y deja la decision final al responsable.

## Estado aplicado en MVP
La primera alerta implementada es `long_session_attention`.

Se activa cuando una sesion abierta supera el rango esperado segun sesiones cerradas de la misma mesa. La salida es una recomendacion de revision operativa, no una conclusion sobre conducta de clientes.

Tambien existe una primera capa de decision reutilizable en `services/decision/policy.py`.

Permite:
- definir una matriz de perdida,
- calcular perdida esperada por accion,
- elegir la accion menos costosa,
- devolver `request_review` cuando la confianza no alcanza el umbral.

Para combinar senales antes de decidir, `services/decision/committee.py` permite promediar distribuciones de probabilidad de varias fuentes ligeras con pesos configurables.

## Siguiente paso tecnico
Crear una capa `services/decision_engine/` con:
- `pressure_index.py`,
- `table_opportunity_score.py`,
- `promise_engine.py`,
- `next_best_action.py`,
- `decision_explainer.py`,
- `feedback_recorder.py`.
