# Local voice samples

Carpeta para pruebas locales del agente de voz.

No subas audios reales al repositorio. Usa esta carpeta solo como ubicacion de trabajo local.

Flujo recomendado:

```powershell
Copy-Item data/local_samples/manifest.example.json data/local_samples/manifest.local.json
```

Graba WAV mono PCM16 a 16 kHz o convierte con FFmpeg:

```powershell
ffmpeg -i entrada.m4a -ac 1 -ar 16000 -sample_fmt s16 data/local_samples/reserva_01.wav
```

Valida la plantilla sin audios:

```powershell
python tools/validate_stt_manifest.py data/local_samples/manifest.example.json --allow-missing-wavs
```

Valida tu corpus real local:

```powershell
python tools/validate_stt_manifest.py data/local_samples/manifest.local.json
```

Benchmark sin STT real:

```powershell
python tools/benchmark_stt_latency.py --manifest data/local_samples/manifest.local.json --engine mock
```
