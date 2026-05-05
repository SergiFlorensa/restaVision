# TTS local con Kokoro ONNX y llamada interactiva

## Decision tecnica

Para la demo local del agente de voz se adopta una capa TTS propia en
`services.voice.tts`. La decision evita acoplar el agente de reservas a un
motor concreto.

Stack recomendado para avanzar:

- STT inicial: Vosk, porque ya funciona en CPU y permite baja latencia.
- TTS avanzado: Kokoro ONNX con modelo `int8`, voz espanola `ef_dora` y
  ejecucion local por CPU.
- Fallback inmediato: Windows SAPI, porque viene integrado en Windows y permite
  comprobar el flujo completo aunque Kokoro no este descargado.
- Testing: adaptador `mock`, para no depender de audio real ni modelos en CI.

## Por que Kokoro ONNX

Kokoro ONNX aporta una voz mas natural que los sintetizadores basicos y evita
introducir PyTorch en el flujo de inferencia local. Para un portatil CPU, el
modelo `int8` es el primer candidato porque reduce tamano y consumo respecto al
modelo completo.

No se versionan modelos ni voces. Los ficheros deben vivir en
`models/checkpoints/`, que queda fuera del control de Git.

## Instalacion

Desde la raiz del proyecto:

```bash
pip install -r requirements/audio.txt
python tools/download_kokoro_tts_assets.py --variant int8
```

Esto descarga:

- `models/checkpoints/kokoro-v1.0.int8.onnx`
- `models/checkpoints/voices-v1.0.bin`

## Prueba rapida de TTS

Con Kokoro:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --text "A que hora le gustaria la reserva?" --play
```

La herramienta aplica una capa previa de prosodia y pronunciacion:

- telefonos por digitos,
- horas en lenguaje natural,
- fechas sin formato numerico,
- pausas mediante puntuacion,
- estilo automatico para preguntas, confirmaciones, reparaciones y casos serios.

Ejemplo:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --text "Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222" --play
```

Con fallback Windows:

```bash
python tools/synthesize_voice_reply.py --engine windows_sapi --text "A que hora le gustaria la reserva?" --play
```

La salida se guarda por defecto en:

```text
data/local_samples/tts_last.wav
```

Tambien se activa cache local por defecto en:

```text
data/local_samples/tts_cache/
```

Esto es importante con Kokoro: la primera sintesis carga el modelo y puede ser
lenta en CPU, pero las frases repetidas del agente se reutilizan como WAV local.

## Llamada interactiva local

Este comando mantiene el hilo de la llamada. Cada turno graba microfono,
transcribe, pasa el texto al agente y reproduce la respuesta.

```bash
python tools/interactive_voice_call.py --device 1 --stt-engine vosk --tts-engine kokoro_onnx --play
```

Por defecto, al iniciar la llamada el agente abre con:

```text
Piemontesa Paseo de Prim, diga.
```

Ese saludo se puede cambiar:

```bash
python tools/interactive_voice_call.py --device 1 --stt-engine vosk --tts-engine kokoro_onnx --play --opening-greeting "Piemontesa Paseo de Prim, buenas tardes, diga."
```

O desactivar para pruebas tecnicas:

```bash
python tools/interactive_voice_call.py --device 1 --stt-engine vosk --tts-engine kokoro_onnx --play --skip-opening-greeting
```

El estilo prosodico se puede fijar manualmente si se quiere comparar:

```bash
python tools/interactive_voice_call.py --device 1 --stt-engine vosk --tts-engine kokoro_onnx --play --tts-style warm
```

Si Kokoro todavia no esta descargado, usar:

```bash
python tools/interactive_voice_call.py --device 1 --stt-engine vosk --tts-engine windows_sapi --play
```

El flujo interactivo resuelve el problema del script anterior, que solo hacia
un turno aislado. Ahora el agente conserva el `call_id` y puede preguntar por
hora, nombre o telefono en turnos sucesivos.

Para medir Kokoro sin cache:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --text "A que hora le gustaria la reserva?" --no-cache
```

## Voces utiles

Voces espanolas disponibles en Kokoro v1.0:

- `ef_dora`: voz femenina, recomendada por defecto.
- `em_alex`: voz masculina.
- `em_santa`: voz masculina alternativa.

Ejemplo:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice em_alex --text "Reserva confirmada para dos personas a las ocho." --play
```

## Criterios de aceptacion para demo

La parte TTS se considera util para demo si:

- genera audio local sin Internet tras descargar los modelos,
- la respuesta corta tarda menos de 1.5 segundos en sintetizar en CPU,
- si Kokoro no llega a 1.5 segundos en frio, las respuestas frecuentes se
  sirven desde cache local en menos de 300 ms,
- el audio se entiende claramente en espanol,
- el flujo interactivo mantiene el contexto de llamada durante varios turnos,
- si Kokoro falla, Windows SAPI permite seguir mostrando la demo completa.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigacion |
|--------|---------|------------|
| Kokoro ONNX instala dependencias pesadas | Puede complicar setup en Windows | Mantener Windows SAPI como fallback |
| Modelo completo demasiado lento | Demo poco fluida | Empezar por `int8` |
| Pronunciacion irregular de nombres o telefonos | Baja naturalidad | Normalizar texto antes de sintetizar |
| Audio largo con peor prosodia | Respuesta menos natural | Mantener frases cortas del agente |
| Redistribucion futura de voces/modelos | Riesgo legal | Revisar licencia concreta antes de vender |

## Siguiente mejora

Medir con muestras reales:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --text "Perfecto, le tomo nota. Me dice el nombre de la reserva?" --play
```

Registrar:

- `synthesis_ms`,
- `duration_ms`,
- `realtime_factor`,
- claridad percibida,
- si el agente necesita acortar o reformular respuestas.
