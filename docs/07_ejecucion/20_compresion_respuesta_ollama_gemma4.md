# Compresion local de respuestas con Ollama y Gemma 4

## Objetivo
Anadir una capa opcional antes del TTS para convertir respuestas correctas pero largas en frases mas telefonicas, naturales y faciles de sintetizar. Esta capa no decide reservas, no inventa disponibilidad y no sustituye la logica determinista del agente.

## Decision para el portatil del TFG
- Modelo recomendado: `gemma4:e2b-it-q4_K_M`.
- Modelo a probar solo en benchmark: `gemma4:e4b-it-q4_K_M`.
- Modelos descartados para el portatil: variantes de 26B/31B y cuantizaciones grandes, por RAM, disco y latencia.
- Para pruebas del problema de latencia, usar el probe Rust como medicion preferente.

En la pagina oficial de Ollama, `gemma4:e2b-it-q4_K_M` aparece con 7.2 GB y `gemma4:e4b-it-q4_K_M` con 9.6 GB. Para un ASUS VivoBook con CPU y sin GPU garantizada, el e2b es el punto de partida razonable. El e4b solo compensa si la latencia real sigue siendo aceptable durante una llamada simulada.

## Instalacion local
Instalar Ollama desde la pagina oficial y descargar el modelo recomendado:

```bash
ollama pull gemma4:e2b-it-q4_K_M
```

Opcional, solo para comparativa:

```bash
ollama pull gemma4:e4b-it-q4_K_M
```

## Prueba rapida de Ollama
```bash
ollama run gemma4:e2b-it-q4_K_M "Resume esta respuesta en una frase corta para telefono: Reserva confirmada para dos personas a las nueve y media."
```

## Prueba con TTS
```bash
python tools/synthesize_voice_reply.py --reply-compressor ollama --reply-compressor-model gemma4:e2b-it-q4_K_M --engine piper --voice-profile castilian_neutral --text "Reserva confirmada para 2 personas el 02/05/2026 a las 21:30, a nombre de Sergi. Muchas gracias, le esperamos en la Piemontesa de Passeig de Prim." --play
```

## Prueba en llamada interactiva
```bash
python tools/interactive_voice_call.py --seconds 7 --device 1 --tts-engine piper --tts-voice-profile castilian_neutral --reply-compressor ollama --reply-compressor-model gemma4:e2b-it-q4_K_M --play
```

## Benchmark 2B frente a 4B
```bash
python tools/benchmark_reply_compressor.py --models gemma4:e2b-it-q4_K_M gemma4:e4b-it-q4_K_M --runs 2
```

La salida muestra `avg_elapsed_ms`, `max_elapsed_ms`, `applied_count` y `fallback_count`. Si e4b aumenta demasiado la latencia, mantener e2b.

## Benchmark turbo en CPU
La configuracion por defecto del compresor usa prompt minimo, `num_predict=24`, `num_ctx=512`, `think=false` y `keep_alive=30m`.

Para un Intel de 4 nucleos fisicos, probar primero 4 threads:

```bash
python tools/benchmark_reply_compressor.py --models gemma4:e2b-it-q4_K_M --runs 2 --timeout 15 --num-thread 4
```

Si sigue lento, comparar 1, 2 y 4 threads:

```bash
python tools/benchmark_reply_compressor.py --models gemma4:e2b-it-q4_K_M --runs 2 --timeout 15 --num-thread 1
python tools/benchmark_reply_compressor.py --models gemma4:e2b-it-q4_K_M --runs 2 --timeout 15 --num-thread 2
python tools/benchmark_reply_compressor.py --models gemma4:e2b-it-q4_K_M --runs 2 --timeout 15 --num-thread 4
```

Esto aplica las recomendaciones practicas de no sobresaturar CPU, comprimir entrada y limitar salida. Si aun asi no baja de 2500 ms, Gemma no debe ir en el camino critico de llamada.

## Preparacion de Gemma para llamada
Gemma debe ejecutarse como asesor de fondo, no como respuesta bloqueante de cada turno.
Antes de una demo conviene parar otros modelos que Ollama mantenga cargados, calentar
Gemma y medir con contexto reducido:

```bash
python tools/prepare_gemma_voice_runtime.py --stop-loaded --model gemma4:e2b-it-q4_K_M --num-thread 4 --num-ctx 256 --num-predict 24 --timeout 40
```

Lectura del resultado:
- `loaded_before` muestra modelos vivos que ocupan RAM.
- `stopped` confirma los modelos descargados de memoria.
- `warmup` puede tardar mucho si Gemma esta frio; si marca timeout pero luego hay probes
  correctos, el modelo ha terminado cargando.
- `first_token_ms` mide cuando empieza a responder.
- `total_ms` mide la respuesta completa.
- Si aparece `model requires more system memory`, cerrar aplicaciones o parar modelos
  con `ollama stop <modelo>`.

Comando recomendado para llamada con Gemma estricta:

```bash
python tools/interactive_voice_call.py --seconds 8 --device 1 --tts-engine piper --tts-voice-profile castilian_neutral --background-advisor ollama --reply-compressor-model gemma4:e2b-it-q4_K_M --ollama-num-thread 4 --background-advisor-num-ctx 256 --background-advisor-num-predict 24 --background-advisor-temperature 0.1 --background-advisor-wait 18 --play
```

El objetivo es que el cliente oiga una frase puente inmediata y Gemma responda unos
segundos despues solo si aporta valor conversacional.

## Probe nativo Rust preferente
Para este problema concreto, el probe Rust es el camino preferente de medicion porque
evita overhead de Python y usa una peticion HTTP minima contra Ollama:

```bash
C:\Users\SERGI\.cargo\bin\rustc.exe tools/native/ollama_stream_probe.rs -O -o tools/native/ollama_stream_probe_rust.exe
tools/native/ollama_stream_probe_rust.exe gemma4:e2b-it-q4_K_M "Cliente: Quiero reservar mesa cerca de la ventana porque viene una persona mayor y prefiere una zona tranquila. Intencion: create_reservation. Respuesta telefonica breve:" --num-thread 4 --num-ctx 256 --num-predict 24
```

La salida importante es:

- `first_response_marker_ms`: tiempo hasta el primer token real.
- `first_period_seen_ms`: tiempo hasta la primera frase completa.
- `collected`: frase generada.

En prueba local con Ollama limpio y Gemma caliente se obtuvo una frase completa en torno
a 2.6 s. Ese valor es aceptable solo porque el agente reproduce antes una frase puente.

## Probe nativo C++ opcional
El repositorio incluye un probe minimo en C++ para medir el overhead nativo de una peticion streaming a Ollama sin pasar por Python:

```bash
g++ tools/native/ollama_stream_probe.cpp -O2 -lws2_32 -o tools/native/ollama_stream_probe.exe
tools/native/ollama_stream_probe.exe gemma4:e2b-it-q4_K_M
```

Este probe no sustituye al agente. Solo ayuda a comparar si el coste esta en Python/HTTP o en la inferencia del modelo. En la prueba local inicial el coste siguio estando en segundos, lo que confirma que el cuello principal es la generacion del modelo en CPU.

## Arquitectura aplicada
El flujo queda asi:

```text
respuesta determinista del agente
-> fast-path por reglas/cache
-> compresor opcional Ollama/Gemma 4 solo si hace falta
-> quality gate de reescritura
-> TTS local
-> audio WAV/reproduccion
```

Para evitar silencio ante peticiones no previstas, existe una segunda via:

```text
peticion compleja del cliente
-> "Entiendo. Lo compruebo un momento."
-> Gemma/Ollama en segundo plano
-> respuesta asesorada si llega dentro del margen configurado
```

Si Ollama no esta instalado, el modelo no esta descargado, la llamada tarda demasiado o la respuesta pierde datos criticos, el sistema conserva la respuesta original del agente.

## Optimizaciones antes y despues de Ollama
Aplicadas en codigo:
- prompt de sistema minimo para reducir prefill,
- `num_predict=24` para limitar tokens de salida,
- `num_ctx=512` en compresion y `num_ctx=256` en asesor de fondo para reducir memoria,
- `think=false` para evitar razonamiento extra si el modelo lo soporta,
- `keep_alive=30m` para mantener el modelo cargado,
- `stop=["\n"]` para cortar salida en una sola frase,
- `num_thread` configurable para buscar el mejor punto de CPU,
- fast-path por reglas para respuestas frecuentes,
- cache en memoria para no repetir la misma reescritura.

Pendiente de benchmark:
- comparar `--num-thread 1`, `--num-thread 2` y `--num-thread 4`,
- medir si el primer turno tras cargar modelo es mucho mas lento que los siguientes,
- dejar Ollama desactivado en llamada si no baja de 2500 ms.

La estrategia preferente queda detallada en:
- `docs/07_ejecucion/21_catalogo_respuestas_offline_gemma.md`

## Reglas de seguridad
- No cambiar nombre, telefono, fecha, hora, personas, direccion, alergias ni decisiones.
- No inventar disponibilidad.
- No usar el LLM para confirmar reservas por si solo.
- Mantener salida de una sola frase oral, salvo que haya datos operativos que preservar.
- Rechazar reescrituras vacias, demasiado largas, con varias lineas o que pierdan numeros/direccion.

## Metricas a observar
- `reply_compression.elapsed_ms`: latencia de Ollama.
- `reply_compression.applied`: si se uso la reescritura.
- `reply_compression.metadata.reason`: motivo de aceptacion o rechazo.
- Latencia total percibida entre final de voz del cliente y respuesta del agente.

Umbrales practicos para demo:
- Excelente: compresion menor de 700 ms.
- Aceptable: compresion menor de 1500 ms.
- Mala: compresion superior a 2500 ms o bloqueo frecuente.

## Criterio de uso
Activar Ollama en demo solo si mejora claramente la naturalidad sin hacer que la llamada parezca lenta. Si no cumple, mantenerlo documentado como modulo experimental y usar el flujo determinista con Piper/Kokoro.

## Fuentes
- Ollama Gemma 4 tags: https://ollama.com/library/gemma4/tags
- Ollama API `/api/generate`: https://github.com/ollama/ollama/blob/main/docs/api.md
