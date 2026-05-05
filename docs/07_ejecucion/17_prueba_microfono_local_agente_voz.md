# Prueba local con microfono

## Objetivo

Probar una llamada simulada sin telefonia real:

```text
microfono
-> WAV local 16 kHz
-> VAD
-> Vosk
-> quality gate
-> agente de voz
-> respuesta textual
```

## Preparacion

Dependencias:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements/audio.txt
```

Modelo usado:

```text
models/checkpoints/vosk-model-small-es-0.42
```

## Ver microfonos disponibles

```powershell
.venv\Scripts\python.exe tools/record_mic_voice_agent.py --list-devices
```

## Prueba rapida

```powershell
.venv\Scripts\python.exe tools/record_mic_voice_agent.py --seconds 7
```

Frase recomendada:

```text
Hola buenas, queria hacer una reserva para dos a las ocho a nombre de Lara telefono seis cero cero uno uno uno dos dos dos
```

## Interpretacion

El resultado relevante es:

```text
vad.has_speech
stt.transcript
transcript_quality.accepted
agent.intent
agent.action_name
agent.reply_text
```

Si el agente pide telefono o hora, no es un fallo grave: significa que el ASR no ha dado un dato suficientemente estructurable y el sistema prefiere preguntar antes que confirmar mal.

## Resultado esperado con Vosk small ES

Vosk small ES es rapido en CPU, pero puede fallar en:

- telefonos dichos con palabras,
- alergias como celiaco,
- frases largas con muletillas,
- horas ambiguas.

Por eso no debe confirmar reservas automaticamente si faltan telefono, hora, personas o nombre.

## Siguiente comparativa

Si Vosk no da precision suficiente, comparar con:

```text
whisper.cpp tiny/base
```

usando el mismo corpus y las mismas metricas.
