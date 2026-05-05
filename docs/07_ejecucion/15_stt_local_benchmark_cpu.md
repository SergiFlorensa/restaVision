# Benchmark STT local en CPU

## Contexto de hardware

Equipo declarado:

```text
VivoBook_ASUSLaptop X515EA_F515EA
Intel64 Family 6 Model 140 Stepping 1 GenuineIntel ~2419 MHz
```

La decision tecnica se orienta a CPU, sin GPU garantizada y sin APIs de pago.

## Objetivo

Medir antes de decidir motor STT:

```text
WAV local
-> VAD/quality gate
-> STT
-> agente de voz
-> metricas
```

No se conectan llamadas reales.

## Modulos anadidos

```text
services/voice/stt.py
services/voice/stt_benchmark.py
tools/benchmark_stt_latency.py
```

## Adaptadores previstos

```text
MockSpeechToTextAdapter
VoskSpeechToTextAdapter
WhisperCppSpeechToTextAdapter
```

El adaptador `mock` permite validar todo el pipeline sin instalar modelos.

`Vosk` y `whisper.cpp` quedan como motores opcionales para comparar latencia y calidad.

## Manifest de benchmark

Formato JSON:

```json
[
  {
    "case_id": "reserva_01",
    "wav_path": "data/local_samples/reserva_01.wav",
    "expected_transcript": "Reserva para 2 a las 20:00 a nombre de Lara telefono 600111222",
    "expected_intent": "create_reservation",
    "expected_action_name": "action_confirm_reservation",
    "expected_slots": {
      "party_size": 2,
      "requested_time_text": "03/05/2026 20:00",
      "customer_name": "Lara",
      "phone": "600111222"
    }
  }
]
```

## Uso

Benchmark sin STT real:

```powershell
python tools/benchmark_stt_latency.py --manifest data/local_samples/manifest.json --engine mock
```

Benchmark Vosk:

```powershell
python tools/benchmark_stt_latency.py `
  --manifest data/local_samples/manifest.json `
  --engine vosk `
  --model-path C:\modelos\vosk-model-small-es
```

Benchmark whisper.cpp:

```powershell
python tools/benchmark_stt_latency.py `
  --manifest data/local_samples/manifest.json `
  --engine whisper.cpp `
  --executable-path C:\tools\whisper.cpp\main.exe `
  --model-path C:\modelos\ggml-base.bin
```

## Metricas calculadas

- tiempo STT,
- factor tiempo real,
- WER,
- VAD aceptado/bloqueado,
- calidad de transcript,
- intent accuracy,
- action accuracy,
- slot field accuracy.

## Criterio de decision para el portatil

Para demo local:

```text
average_realtime_factor <= 0.6 ideal
average_realtime_factor <= 1.0 aceptable
average_wer <= 0.20 aceptable
intent_accuracy >= 0.90
slot_field_accuracy >= 0.85
blocked_count correcto para silencio/ruido
```

## Decision recomendada

Primero ejecutar benchmark con `mock` para validar pipeline.

Despues probar:

1. Vosk small ES como referencia de latencia.
2. whisper.cpp tiny/base como referencia de calidad.
3. Elegir con datos.

Silero VAD sigue fuera del primer paso. Se incorpora solo si las pruebas con ruido muestran que el VAD simple no separa bien voz/silencio.
