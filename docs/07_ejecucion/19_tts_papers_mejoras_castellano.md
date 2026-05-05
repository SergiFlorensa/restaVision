# Extraccion tecnica TTS: EfficientSpeech y VITS

## Documentos revisados

- `2305.13905v1.pdf`: EfficientSpeech, modelo TTS on-device.
- `kim21f.pdf`: VITS, TTS end-to-end con VAE, flujos y entrenamiento adversarial.

## Conclusiones aplicables a RestaurIA

1. No aportan una voz castellana autoctona lista para integrar.
   - Ambos papers son arquitectura/modelado.
   - No sustituyen directamente a Kokoro ONNX en el MVP local.

2. EfficientSpeech refuerza nuestra decision local-first.
   - El paper prioriza inferencia local, bajo consumo, RTF y CPU.
   - Aplicacion directa: mantener TTS por adaptador, medir latencia y usar cache de respuestas frecuentes.

3. VITS explica por que la naturalidad depende del ritmo y la duracion.
   - La mejora de naturalidad viene de duraciones, pitch, ritmo y variacion prosodica.
   - Aplicacion directa: evitar frases largas, generar respuestas breves y bien puntuadas.

4. Ambos papers insisten indirectamente en el preprocesado textual.
   - Text normalization y phonemization aparecen como parte previa clave del sistema TTS.
   - Aplicacion directa: normalizar las respuestas del agente antes de enviarlas al motor de voz.

## Mejora incorporada

Se ha ampliado `services.voice.tts.prepare_text_for_tts` para convertir respuestas ASCII del agente en texto mas natural para sintesis espanola:

- `A que` -> `A qué`
- `gustaria` -> `gustaría`
- `telefono` -> `teléfono`
- `Si,` -> `Sí,`
- `situacion` -> `situación`
- `celiaca` -> `celíaca`
- signos iniciales `¿` y `¡` cuando proceda

Esto no cambia la logica del agente ni rompe tests existentes: solo mejora el texto que recibe Kokoro/Windows SAPI.

## Decision

No se recomienda implementar EfficientSpeech ni entrenar VITS ahora:

- requieren dataset, entrenamiento y validacion de voz,
- no garantizan mejor castellano que Kokoro sin un corpus espanol adecuado,
- aumentan mucho el alcance del TFG,
- no resuelven por si solos la voz castellana autoctona.

La ruta correcta para el MVP sigue siendo:

1. Kokoro ONNX `int8` como TTS natural local.
2. Cache de respuestas frecuentes.
3. Normalizacion espanola previa.
4. Frases cortas y operativas.
5. Evaluacion manual de voces espanolas disponibles: `ef_dora`, `em_alex`, `em_santa`.

## Siguiente validacion recomendada

Probar las tres voces con la misma frase:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice ef_dora --text "A que hora le gustaria la reserva?" --play
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice em_alex --text "A que hora le gustaria la reserva?" --play
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice em_santa --text "A que hora le gustaria la reserva?" --play
```

Elegir la que suene mas clara, sobria y cercana para un restaurante en Espana.

## Extraccion adicional: control de acento

Documentos revisados:

- `2409.09352v2.pdf`: MacST, conversion multiacento mediante transliteracion textual.
- `2603.07534v1.pdf`: Accent Vector, manipulacion controlable de acento con vectores de parametros.
- `2410.03734v1.pdf`: conversion de acento con unidades discretas y datos paralelos sinteticos.

Conclusiones tecnicas aplicables:

1. El acento no se corrige de forma fiable solo con filtros de audio.
   - Los tres documentos tratan el acento como combinacion de fonemas, duracion, prosodia y parametros internos del modelo.
   - Para el MVP no conviene prometer "convertir" una voz latinoamericana en castellano peninsular solo con ecualizacion.

2. La idea de control por intensidad si es util para nuestro diseno.
   - Accent Vector escala e interpola componentes de acento.
   - En RestaurIA se traduce en perfiles de voz versionables: motor, voz, velocidad, normalizacion textual y reglas de cadencia.

3. MacST refuerza el valor de preparar el texto antes del TTS.
   - El paper usa transliteracion para provocar rasgos de pronunciacion.
   - En nuestro caso no conviene transliterar castellano, pero si normalizar datos operativos: horas, telefonos, nombres de servicio y preguntas.

4. La conversion neural real queda fuera del MVP local CPU.
   - Los enfoques con LoRA, HuBERT, wav2vec, MBart, YourTTS o datos paralelos requieren entrenamiento y validacion.
   - Puede documentarse como fase experimental, no como dependencia del TFG.

## Mejora incorporada: perfil `castilian_neutral`

Se ha anadido una capa de perfil de voz en `services.voice.tts`:

- `VOICE_RENDERING_PROFILES`
- `DEFAULT_VOICE_PROFILE`
- `TextToSpeechConfig.voice_profile`
- `prepare_text_for_tts(..., voice_profile="castilian_neutral")`
- `build_tts_adapter(..., voice_profile="castilian_neutral")`

El perfil `castilian_neutral` aplica:

- velocidad efectiva `0.94` sobre el motor TTS para una cadencia menos precipitada,
- puntuacion de servicio mas sobria,
- ajuste de frases de restaurante:
  - `Perfecto me dice el nombre?` -> `Perfecto. ¿Me dice su nombre?`
  - `A que hora le gustaria la reserva?` -> `Perfecto. ¿A qué hora le gustaría hacer la reserva?`
- normalizacion operativa ya existente de fechas, horas, telefonos y numero de comensales.

Esto no clona voz ni convierte acento a nivel neuronal. Es una mejora segura, local, medible y compatible con Kokoro ONNX y Windows SAPI.

## Como probarlo

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice-profile castilian_neutral --text "Piemontesa Paseo de Prim, diga. Perfecto me dice el nombre?" --play
```

Comparar contra el perfil neutro:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice-profile default --text "Piemontesa Paseo de Prim, diga. Perfecto me dice el nombre?" --play
```

En llamada interactiva:

```bash
python tools/interactive_voice_call.py --tts-engine kokoro_onnx --tts-voice-profile castilian_neutral --play
```

## Siguiente paso tecnico

Para mejorar realmente el acento peninsular, el siguiente paso no es tocar mas puntuacion, sino comparar motores/voces:

1. Mantener Kokoro como motor natural actual.
2. Anadir Piper como motor alternativo con voces `es_ES`.
3. Medir naturalidad subjetiva, latencia, claridad y aceptacion del encargado.
4. Solo despues valorar conversion/clonado de voz con consentimiento, como experimento aislado.

## Extraccion fonetica aplicada: castellano peninsular profesional

Fuentes revisadas:

- RAE/ASALE, `Nueva gramatica. Fonetica y fonologia` y recursos sobre acento.
- Instituto Cervantes, `Plan curricular: pronunciacion y prosodia`.
- Estebas-Vilaplana y Prieto, `Castilian Spanish Intonation`.
- Estebas-Vilaplana y Prieto, revision de `Sp_ToBI`.
- Timothy L. Face, `The role of intonation cues in the perception of declaratives and absolute interrogatives in Castilian Spanish`.
- PRESEEA_PROSODIA.
- Cantero Serena, `Fonetica y didactica de la pronunciacion` y `Analisis Melodico del Habla`.

Extraccion accionable:

1. Variedad objetivo.
   - Usar espanol peninsular estandar, no "espanol neutro" generico.
   - Evitar seseo, ceceo, aspiracion de `s`, perdida marcada de consonantes finales y cadencias regionales fuertes.
   - Aplicacion: el perfil se llama `castilian_neutral` y no promete neutralidad panhispanica.

2. Segmentos y vocales.
   - Mantener vocales limpias y estables.
   - No introducir reduccion vocal fuerte.
   - Aplicacion: normalizacion de acentos graficos y palabras frecuentes antes de sintetizar.

3. Tonicidad.
   - RAE distingue palabras tonicas y atonas; articulos, preposiciones, conjunciones, posesivos antepuestos y pronombres atonos no deben recibir foco salvo contraste.
   - Aplicacion: no se insertan pausas entre articulo/preposicion y su nucleo; las pausas se reservan para datos operativos.

4. Entonacion.
   - Face muestra que las interrogativas absolutas castellanas se perciben por pistas de F0, especialmente el movimiento final.
   - Estebas-Prieto/Sp_ToBI refuerzan la diferencia entre cierre bajo, continuidad y peticion.
   - Aplicacion: preguntas con signos `¿?`, afirmaciones con punto, continuidad con coma/dos puntos y peticiones con cadencia amable.

5. Ritmo y agrupacion.
   - Cantero insiste en que el habla se organiza jerarquicamente y que acento, ritmo y entonacion interactuan.
   - Aplicacion: agrupar por sintagmas y datos; evitar ritmo palabra-a-palabra.

6. Uso conversacional.
   - PRESEEA_PROSODIA plantea la prosodia como fenomeno de uso y variacion.
   - Aplicacion: el agente no debe sonar como lectura plana; debe variar segun reserva, confirmacion, reparacion o situacion sensible.

## Mejora incorporada desde esta extraccion

Se ha ampliado `castilian_neutral` con:

- `CASTILIAN_NEUTRAL_VOICE_PROMPT`, preparado para motores TTS futuros que acepten prompt/instrucciones de estilo.
- Foco informativo mediante puntuacion:
  - `Reserva confirmada para dos personas el 2 de mayo a las nueve...`
  - pasa a:
  - `Reserva confirmada: para dos personas, el 2 de mayo, a las nueve...`
- Pausa clara antes de telefonos:
  - `Telefono 600111222`
  - pasa a:
  - `Telefono: seis cero cero, uno uno uno, dos dos dos`
- El perfil sigue siendo compatible con Kokoro ONNX y Windows SAPI.

Limitacion:

- Estas reglas mejoran ritmo, timing y foco, pero no cambian el acento neural de la voz si el modelo base suena latino. Para eso hace falta seleccionar una voz `es_ES` mejor o introducir un motor alternativo como Piper.

## Correccion real de acento: motor Piper `es_ES`

Problema detectado en prueba manual:

- Kokoro mejora con puntuacion, pausas y perfil `castilian_neutral`.
- Aun asi, la voz base puede seguir sonando latinoamericana porque el timbre/acento pertenece al modelo/voz, no al texto.

Decision aplicada:

- Se incorpora `piper-tts==1.4.2` como motor TTS local opcional.
- Se anade el adaptador `PiperTextToSpeechAdapter`.
- El motor por defecto de las herramientas locales pasa a ser `piper` para probar voces `es_ES`.
- Voz inicial recomendada: `es_ES-davefx-medium`.

Comandos:

```bash
python tools/download_piper_tts_assets.py --voice davefx
python tools/synthesize_voice_reply.py --engine piper --voice-profile castilian_neutral --text "Piemontesa Paseo de Prim, diga. Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222." --play
```

Comparacion contra Kokoro:

```bash
python tools/synthesize_voice_reply.py --engine kokoro_onnx --voice-profile castilian_neutral --text "Piemontesa Paseo de Prim, diga. Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222." --play
```

Otra voz `es_ES` disponible para comparar:

```bash
python tools/download_piper_tts_assets.py --voice sharvard
python tools/synthesize_voice_reply.py --engine piper --model-path models/checkpoints/piper/es_ES-sharvard-medium.onnx --voices-path models/checkpoints/piper/es_ES-sharvard-medium.onnx.json --voice es_ES-sharvard-medium --voice-profile castilian_neutral --text "Piemontesa Paseo de Prim, diga. Reserva confirmada para 2 personas el 02/05/2026 a las 21:30. Telefono 600111222." --play
```

Muestras generadas:

- `data/local_samples/tts_piper_es_es_davefx.wav`
- `data/local_samples/tts_piper_es_es_sharvard.wav`

Notas de licencia:

- El paquete Python usado en Windows declara `GPL-3.0-or-later`.
- Es aceptable para TFG/demo local, pero debe revisarse antes de comercializar.
- Los modelos de voz descargados quedan en `models/checkpoints/piper/` y no se versionan.
