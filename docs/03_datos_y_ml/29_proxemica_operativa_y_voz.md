# Proxemica operativa y avisos de voz

## Proposito
Este documento traduce la proxemica de Edward T. Hall a software de forma prudente y operativa.

La idea no es inferir emociones, conflicto, intenciones ni rasgos culturales de personas concretas. La idea util para RestaurIA es medir:
- distancias calibradas en metros,
- contactos staff-mesa,
- densidad por zona,
- proximidad entre tracks,
- y mensajes operativos de baja intrusividad.

## Implementacion actual
Codigo:
- `services/proxemics/engine.py`
- `services/proxemics/voice.py`

Tests:
- `tests/test_proxemics.py`

El modulo trabaja sobre coordenadas de suelo en metros. Por tanto, antes de usarlo con video real hace falta calibracion u homografia. No debe aplicarse directamente a pixeles de camara como si fueran metros.

## Motor proxemico
`ProxemicAnalyzer` ofrece:
- `classify_distance()`: clasifica una distancia como `intimate`, `personal`, `social`, `public` u `out_of_range`,
- `pairwise_interactions()`: calcula interacciones entre personas detectadas,
- `staff_table_contacts()`: identifica presencia de staff cerca de mesas ocupadas,
- `assess_crowding()`: estima densidad operativa por zona.

La salida usa etiquetas neutrales:
- `direct_service_contact`,
- `nearby_service_presence`,
- `table_attention_contact`,
- `close_proximity_review`,
- `shared_social_area`.

No usa etiquetas acusatorias como robo, acoso, conflicto o impago.

## Perfil proxemico
`ProxemicProfile` define umbrales base:
- distancia intima: hasta `0.45 m`,
- distancia personal: hasta `1.20 m`,
- distancia social: hasta `3.60 m`,
- distancia publica: hasta `7.60 m`.

Tambien incluye `distance_multiplier` para ajustar sensibilidad por despliegue. Este ajuste debe tratarse como configuracion operativa, no como verdad cultural rigida.

## Densidad operativa
`assess_crowding()` clasifica densidad por zona:
- `normal`,
- `elevated`,
- `high`.

La interpretacion recomendada es operacional:
- revisar flujo,
- evitar saturacion del dashboard,
- priorizar atencion,
- medir si la densidad degrada la fiabilidad de estados.

No se debe traducir automaticamente a estres individual de clientes.

## Avisos de voz
`ProxemicVoiceFormatter` genera frases breves y no invasivas:
- densidad elevada,
- densidad alta,
- atencion cercana registrada,
- proximidad muy alta a revisar.

`VoiceMessageLimiter` evita repetir la misma alerta durante una ventana de tiempo.

Principio:
- la voz debe ser un refuerzo puntual,
- no debe convertirse en canal principal,
- no debe acusar ni sobredramatizar.

## Encaje en el pipeline futuro

```text
frame
  -> deteccion/tracking
  -> homografia a coordenadas de suelo
  -> tracks en metros
  -> ProxemicAnalyzer
  -> eventos/metricas operativas
  -> dashboard o aviso de voz limitado
```

## Que queda pospuesto
Queda fuera de la fase actual:
- deteccion de postura u orientacion corporal,
- inferencia de mirada,
- identificacion de relaciones entre clientes,
- eventos sociales persistidos en base de datos,
- perfiles culturales avanzados,
- agente de voz conversacional.

Motivo:
- hacen falta datos reales,
- la precision de metros depende de calibracion,
- y las inferencias sociales son sensibles si se convierten en decisiones automaticas.

## Criterio profesional
Este modulo aporta informacion para el software cuando se use como:
- metrica de contexto,
- senal de servicio,
- indicador de densidad,
- criterio de visualizacion,
- o entrada a analitica futura.

No debe usarse para juzgar personas. Debe ayudar al responsable de sala a leer mejor el estado operativo.
