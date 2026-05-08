# Mejora local de calidad de voz TTS

## Objetivo
Mantener Piper como motor principal y mejorar la salida vocal mediante:

- texto mas oral antes del TTS,
- perfiles prosodicos por situacion,
- postprocesado Rust del WAV,
- comparativas A/B frente a Kokoro.

La capa Rust no cambia el acento del modelo. Sirve para ganar estabilidad,
claridad, volumen percibido y acabado de canal.

## Evidencia extraida

### SpeechAndAudioProcessingForCod.15.pdf
- La calidad de voz debe evaluarse con escucha humana tipo MOS.
- El postfiltrado puede reducir aspereza perceptiva.
- La telefonia clasica usa banda estrecha aproximada 200-3400 Hz.
- Las modulaciones temporales son importantes para inteligibilidad; conviene evitar
  lectura plana y parrafos largos.

Aplicacion en RestaurIA:
- test A/B Piper/Kokoro,
- preset `clarity` para demo general,
- preset `phone` para simular llamada,
- compresion ligera y normalizacion de pico.

### 2021.conll-1.42.pdf
- La prosodia puede controlarse desde el texto con marcas de foco.
- Las palabras enfocadas cambian F0, intensidad, duracion y pausas.

Aplicacion en RestaurIA:
- enfatizar datos operativos con puntuacion y frases cortas,
- pausar cerca de hora, nombre, telefono, personas, alergias y cambios,
- evitar enfasis en articulos/preposiciones.

### FULLTEXT01.pdf
- La naturalidad conversacional depende de F0, variacion de F0 y speech rate.
- El habla espontanea tiene mas variabilidad que el habla leida.
- Segmentar en grupos respiratorios ayuda a conservar naturalidad.

Aplicacion en RestaurIA:
- usar perfiles `castilian_neutral` y `castilian_service`,
- variar velocidad segun situacion,
- no mandar respuestas largas al TTS si pueden dividirse.

## Postprocesado Rust

Fuente:

```text
tools/native/voice_postprocess.rs
```

Compilacion:

```powershell
C:\Users\SERGI\.cargo\bin\rustc.exe tools\native\voice_postprocess.rs -O -o tools\native\voice_postprocess.exe
```

Presets:

| Preset | Uso | Procesado |
|--------|-----|-----------|
| `clarity` | Demo general | high-pass suave, compresion ligera, normalizacion |
| `warm` | Voz menos agresiva | high-pass mas bajo, compresion suave |
| `phone` | Simulacion telefonica | paso-banda telefonico, compresion mas fuerte |

## Prueba rapida

```powershell
.\.venv\Scripts\python.exe tools\synthesize_voice_reply.py --engine piper --voice-profile castilian_service --voice-postprocess clarity --text "De acuerdo. Lo reviso un momento. Me confirma un telefono de contacto?" --play
```

Comparar efecto telefonico:

```powershell
.\.venv\Scripts\python.exe tools\synthesize_voice_reply.py --engine piper --voice-profile castilian_service --voice-postprocess phone --text "Reserva confirmada para dos personas a las nueve y media, a nombre de Sergi. Gracias, le esperamos en la Piemontesa de Passeig de Prim." --play
```

Uso en llamada local:

```powershell
.\.venv\Scripts\python.exe tools\interactive_voice_call.py --seconds 8 --device 1 --tts-engine piper --tts-voice-profile castilian_service --voice-postprocess clarity --background-advisor ollama --reply-compressor-model gemma4:e2b-it-q4_K_M --ollama-num-thread 4 --background-advisor-num-ctx 256 --background-advisor-num-predict 24 --background-advisor-temperature 0.1 --background-advisor-wait 18 --play
```

## Criterio de decision
Mantener `clarity` si:

- mejora claridad sin sonar artificial,
- no introduce chasquidos,
- no fatiga la escucha,
- conserva nombres, telefonos y horas inteligibles.

Usar `phone` solo para demo de llamada, no como voz general de sala.
