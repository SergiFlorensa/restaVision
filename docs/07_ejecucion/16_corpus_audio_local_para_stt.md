# Corpus audio local para STT

## Objetivo

Preparar el primer corpus pequeno de audios locales para decidir con datos si el portatil aguanta Vosk, whisper.cpp o faster-whisper.

No se usan llamadas reales.

## Ubicacion

```text
data/local_samples/
```

Archivos versionados:

```text
data/local_samples/README.md
data/local_samples/manifest.example.json
```

Archivos no recomendados para git:

```text
*.wav
manifest.local.json si contiene datos reales
```

## Frases minimas que hay que grabar

Graba estas muestras con voz normal, como si llamaras al restaurante:

1. `reserva_completa_01.wav`

```text
Reserva para 2 a las 20:00 a nombre de Lara telefono 600111222
```

2. `cancelacion_01.wav`

```text
Quiero cancelar mi reserva telefono 600111222
```

3. `alergia_01.wav`

```text
Queria reservar mesa para 2 a las 21:00 soy celiaco
```

4. `horario_01.wav`

```text
Hola queria saber el horario de cocina
```

5. `silencio_01.wav`

```text
3 segundos de silencio o ruido ambiente sin hablar
```

## Formato tecnico

Formato recomendado:

```text
WAV
PCM16
mono
16000 Hz
3-8 segundos por muestra
```

Conversion con FFmpeg:

```powershell
ffmpeg -i entrada.m4a -ac 1 -ar 16000 -sample_fmt s16 data/local_samples/reserva_completa_01.wav
```

## Validacion

Primero valida la plantilla:

```powershell
python tools/validate_stt_manifest.py data/local_samples/manifest.example.json --allow-missing-wavs
```

Despues crea tu copia local:

```powershell
Copy-Item data/local_samples/manifest.example.json data/local_samples/manifest.local.json
```

Cuando ya existan los WAV:

```powershell
python tools/validate_stt_manifest.py data/local_samples/manifest.local.json
```

## Benchmark inicial

Sin STT real:

```powershell
python tools/benchmark_stt_latency.py --manifest data/local_samples/manifest.local.json --engine mock
```

Esto valida:

- manifest,
- WAV,
- VAD,
- quality gate,
- agente de voz,
- metricas de slots e intenciones.

## Siguiente decision

Cuando el corpus local pase con `mock`, instalar o configurar un solo motor:

1. Vosk small ES si priorizamos latencia.
2. whisper.cpp tiny/base si priorizamos precision.

No instalar ambos a la vez hasta tener el corpus listo.
