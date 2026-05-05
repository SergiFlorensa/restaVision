# Quality gate de audio local para agente de voz

## Objetivo

Preparar RestaurIA para pruebas de voz locales sin llamadas reales y sin dependencias pesadas.

La capa evita que silencio, ruido, transcripciones repetitivas o baja confianza lleguen al agente de reservas como si fueran una llamada fiable.

## Pipeline aplicado

```text
WAV local PCM16
-> lectura y metadatos
-> VAD simple por energia/RMS
-> calidad de transcript opcional
-> WER normalizado si hay referencia
-> decision accepted_for_agent
```

## Modulos

```text
services/voice/audio_quality.py
tools/evaluate_voice_audio_quality.py
```

Endpoint:

```text
POST /api/v1/voice/audio/quality
```

## Por que VAD simple primero

Se empieza con un VAD ligero por energia/RMS porque:

- no requiere PyTorch,
- no anade peso al setup,
- funciona en CPU,
- permite medir antes de decidir Silero VAD,
- bloquea silencio y audio demasiado corto.

Silero VAD queda como mejora opcional si las pruebas con ruido de restaurante muestran que el VAD simple no basta.

## Quality gate

El sistema bloquea si:

- no hay habla suficiente,
- el transcript esta vacio,
- hay muy pocos tokens,
- la transcripcion parece repetitiva,
- la confianza STT simulada es baja,
- el WER contra referencia supera el umbral.

## Uso local

```powershell
python tools/evaluate_voice_audio_quality.py data/local_samples/reserva_01.wav `
  --transcript "Reserva para cuatro personas a las nueve" `
  --reference "Reserva para 4 personas a las 9" `
  --confidence 0.92
```

## Criterio de aceptacion para demo

Antes de conectar Whisper, Vosk, microfono o frontend:

- silencio bloqueado,
- audio con voz aceptado,
- transcript repetitivo bloqueado,
- WER normalizado funcionando,
- ninguna accion del agente se ejecuta si `accepted_for_agent=false`.

## Siguiente paso

Integrar un adaptador STT intercambiable:

```text
SpeechToTextAdapter
├─ VoskSpeechToTextAdapter
├─ WhisperCppSpeechToTextAdapter
└─ MockSpeechToTextAdapter
```

El benchmark debe decidir con datos si el portatil aguanta `whisper.cpp` o si conviene Vosk como modo rapido.
