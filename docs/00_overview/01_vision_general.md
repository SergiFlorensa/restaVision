# Visión general del proyecto

## Nombre de trabajo
RestaurIA / Smart Restaurant AI

## Problema
En restaurantes con alta ocupación, el director o responsable de sala toma decisiones críticas bajo presión:
- qué grupo aceptar,
- cuánto tiempo de espera prometer,
- qué mesa se liberará antes,
- cuándo recombinar mesas,
- qué mesa está desatendida,
- cuándo existe riesgo operativo o de impago.

Normalmente estas decisiones se toman con intuición, información parcial y mucho estrés.

## Propuesta de solución
Sistema local de visión e inteligencia operacional que:
1. observa la sala con cámaras,
2. convierte lo visual en eventos operativos,
3. estima tiempos y detecta patrones,
4. recomienda decisiones,
5. notifica de forma visual y no intrusiva.

## Principios del sistema
- utilidad operativa por encima de sofisticación técnica,
- latencia baja,
- explicabilidad,
- privacidad por diseño,
- modularidad,
- trazabilidad de decisiones.

## Resultado esperado
Un software que permita responder preguntas como:
- “¿Cuánto falta para que se libere una mesa para 7?”
- “¿Qué mesa tiene mayor probabilidad de acabar en menos de 10 minutos?”
- “¿Qué mesas están en fase de pago o finalización?”
- “¿Dónde hay cuello de botella?”
- “¿Qué acciones anómalas merecen atención?”

## Alcance del MVP
El MVP no intenta resolver todo. Se centra en:
- ocupación/liberación de mesas,
- número de personas por mesa,
- detección básica de eventos,
- medición de tiempos,
- predicción simple de liberación,
- dashboard operativo.

## Alcance posterior
- multi-mesa,
- multi-cámara,
- recomendación automática de asignación,
- anomalías operativas e impago,
- alertas discretas,
- integración con TPV/POS y reservas.
