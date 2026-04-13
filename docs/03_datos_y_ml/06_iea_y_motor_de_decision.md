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
- score de riesgo de impago.

### Explicabilidad
Toda recomendación debe poder justificar:
- variables clave,
- eventos recientes,
- nivel de confianza.

## Regla clave
El sistema no acusa ni decide por sí solo sobre personas. Señala riesgos operativos y deja la decisión humana al responsable.
