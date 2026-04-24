# Capa inteligente de explotación y apoyo a decisión

## Qué significa aquí “IEA”
En este proyecto, la capa IEA se entiende como la capa que:
- interpreta el estado operativo,
- prioriza alertas,
- recomienda decisiones,
- explica por qué sugiere algo.

## Componentes
### Máquina de estados
Ejemplo:
- libre,
- ocupada,
- esperando,
- comiendo,
- finalizando,
- pago,
- vacía,
- lista.

### Motor de reglas
Ejemplo:
- si una mesa tiene alta probabilidad de liberación y entra un grupo compatible, sugerir asignación.

### Scoring
Ejemplos:
- score de liberación,
- score de congestión,
- score de anomalía,
- score de riesgo operativo revisable.

### Explicabilidad
Toda recomendación debe poder justificar:
- variables clave,
- eventos recientes,
- nivel de confianza.

## Regla clave
El sistema no acusa ni decide por sí solo sobre personas. Señala riesgos operativos y deja la decisión humana al responsable.

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
