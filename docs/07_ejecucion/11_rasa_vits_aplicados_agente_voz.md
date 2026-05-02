# Rasa y VITS aplicados al agente de voz

Fuentes analizadas:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\1712.05181v2.pdf
C:\Users\SERGI\Desktop\visionRestaIA Libros\2106.06103v1.pdf
```

## Decision

No se anade Rasa como dependencia ni se entrena un modelo VITS propio. Para el alcance actual del TFG seria demasiado pesado y no resolveria el cuello principal.

Si se aplican dos ideas importantes:

1. De Rasa: separar conversacion en intencion, estado, accion y eventos.
2. De VITS: cuidar la normalizacion textual antes de sintetizar voz.

## Aporte extraido de Rasa

Rasa plantea que el dialogo no debe ser solo texto libre. Cada turno deberia producir:

- intencion,
- entidades/slots,
- estado conversacional,
- accion elegida,
- eventos trazables.

Aplicacion en RestaurIA:

```text
transcript -> intent/slots -> VoiceCall -> action_name -> reply_text
```

El agente ahora devuelve `action_name` y `action_payload` en cada turno.

Ejemplos:

```text
utter_ask_requested_time
action_confirm_reservation
action_reject_reservation
action_cancel_reservation
action_escalate_to_manager
```

Esto es importante porque el frontend, Asterisk o un futuro motor TTS no deben inferir la accion leyendo el texto. Deben recibir una accion estructurada.

## Aporte extraido de VITS

VITS es un modelo avanzado de text-to-speech. No es razonable entrenarlo en este proyecto, pero su planteamiento confirma algo importante:

```text
la calidad de voz no depende solo del modelo, tambien del texto de entrada.
```

Aplicacion en RestaurIA:

- no mandar al TTS fechas crudas como `08/05/2026 21:30`,
- generar texto mas natural:

```text
el 8 de mayo a las 21:30
```

Nuevo modulo:

```text
services/voice/speech_text.py
```

## Que se descarta por ahora

### Rasa completo

No se instala porque:

- introduce peso de dependencias,
- requiere entrenamiento y dataset,
- el dominio actual todavia cabe en reglas controladas,
- el MVP necesita determinismo.

Puede tener sentido mas adelante si se recopilan suficientes conversaciones reales.

### VITS propio

No se entrena porque:

- requiere dataset de voz,
- requiere GPU o mucho tiempo de entrenamiento,
- no aporta al MVP tanto como usar Piper local,
- la prioridad es dialogo operativo, no investigacion TTS.

## Resultado aplicado

El agente queda mas preparado para producto:

- accion estructurada para UI/Asterisk,
- trazabilidad tipo dialog manager,
- texto de respuesta mas natural para TTS,
- sin dependencias pesadas.
