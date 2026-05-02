# Agente de voz local para reservas

## Objetivo

Definir una ruta realista para construir un agente de voz que responda llamadas de restaurante como apoyo al encargado de sala, sin depender de servicios de pago ni hardware especial.

El agente no debe ser un chatbot generico. Debe ser un operador de reservas conectado al estado operativo de RestaurIA:

- reservas existentes,
- disponibilidad teorica de mesas,
- estado real de sala,
- cola,
- ETA de liberacion,
- reglas del restaurante,
- criterios de escalado al encargado.

## Enfoque recomendado

La primera version no deberia conectarse directamente a una linea telefonica real. Para el TFG es mas seguro, barato y demostrable empezar con un simulador de llamada en navegador:

```text
microfono navegador
  -> VAD
  -> STT local
  -> clasificador de intencion
  -> gestor de dialogo
  -> motor de disponibilidad
  -> respuesta controlada
  -> TTS local
```

Cuando esta cadena funcione, la integracion telefonica real se puede plantear con Asterisk/VoIP.

## Arquitectura del agente

### 1. Entrada de audio

Para prototipo:

- microfono del navegador,
- WebSocket hacia FastAPI,
- audio en chunks cortos,
- deteccion de fin de turno con VAD.

Para fase avanzada:

- Asterisk con ARI,
- canal de media externo,
- audio RTP hacia un servicio local.

### 2. VAD

El VAD decide cuando empieza y termina una frase. Esto es clave para latencia y fluidez.

Opciones:

- Silero VAD: buena opcion local, ligera y con licencia MIT.
- WebRTC VAD: muy rapido, clasico, util si se busca latencia minima.

Decision MVP:

- usar VAD solo para cortar turnos de habla;
- no usar palabra de activacion en llamada telefonica;
- timeout corto para evitar silencios largos;
- permitir interrupcion humana en fases futuras.

### 3. Speech-to-text

Opciones viables:

- Vosk: recomendado para MVP por latencia baja, streaming, modelos pequenos y vocabulario configurable.
- whisper.cpp: mejor como segunda linea para mayor calidad, pero puede tener mas latencia en CPU.
- faster-whisper: buena opcion si el portatil aguanta CPU int8 o si hay GPU, pero anade mas peso de dependencias.

Decision MVP:

- Vosk para intenciones cortas de reserva;
- vocabulario acotado: reservar, cancelar, cambiar, personas, hora, nombre, telefono;
- whisper.cpp solo como experimento comparativo posterior.

### 4. Entendimiento de intencion

No conviene empezar con un LLM libre contestando sin control. En llamadas reales hay que ser determinista.

Intenciones iniciales:

- `crear_reserva`
- `cancelar_reserva`
- `modificar_reserva`
- `consultar_disponibilidad`
- `confirmar_llegada`
- `consultar_horario`
- `hablar_con_encargado`

Entidades iniciales:

- nombre,
- telefono,
- fecha,
- hora,
- numero de personas,
- preferencia de zona,
- comentario breve.

Herramientas posibles:

- reglas y expresiones regulares propias para MVP,
- dateparser para fechas y horas en lenguaje natural,
- Rasa Open Source si el dialogo crece,
- spaCy solo si hace falta NER adicional en espanol,
- Duckling si se quiere extraccion robusta de fechas, horas y cantidades.

Decision MVP:

- empezar con reglas + dateparser;
- documentar ejemplos reales;
- entrenar NLU solo cuando haya frases suficientes.

### 5. Gestor de dialogo

El agente debe funcionar por estados, no por conversacion libre.

Estados minimos:

```text
inicio
  -> identificar_motivo
  -> recoger_datos
  -> consultar_disponibilidad
  -> confirmar_accion
  -> ejecutar_accion
  -> cierre
```

Reglas importantes:

- si falta un dato, preguntar solo ese dato;
- confirmar antes de crear/cancelar/modificar;
- no prometer mesa si el motor de disponibilidad no lo permite;
- escalar al encargado ante conflicto, queja, grupo grande o baja confianza;
- respuesta corta, natural y sin explicaciones tecnicas.

### 6. Motor de disponibilidad

Esta es la parte diferencial frente a un bot telefonico normal.

El agente consulta:

- reservas por franja horaria,
- mesas bloqueadas,
- aforo por mesa,
- duracion media por tipo de grupo,
- estado real de sala,
- cola actual,
- ETA de liberacion,
- margen de seguridad.

Ejemplo:

```text
Cliente: Queria mesa para 4 a las 21:30.
Agente:
  - revisa reservas,
  - revisa mesas aptas para 4,
  - revisa si hay una mesa que probablemente libere antes,
  - calcula riesgo,
  - ofrece 21:30, 21:45 o rechazo educado.
```

### 7. Generacion de respuesta

La respuesta debe salir de plantillas controladas, no de texto libre sin validar.

Ejemplos:

```text
Si, tengo disponibilidad para {personas} personas a las {hora}.
La reserva quedaria a nombre de {nombre}. Me confirma un telefono de contacto?
```

```text
Ahora mismo no puedo garantizar mesa a las {hora}.
Puedo ofrecerle {hora_alternativa} o apuntarle en lista de espera.
```

```text
He localizado su reserva a nombre de {nombre} para {personas} personas a las {hora}.
La cancelo?
```

### 8. Text-to-speech

Opciones viables:

- Piper: recomendado para voz local por calidad, rapidez y voces disponibles en espanol.
- eSpeak NG: fallback muy ligero, menos natural.
- voces del sistema operativo: utiles para pruebas, pero menos controlables y menos reproducibles.

Decision MVP:

- Piper con voz espanola `medium`;
- frases cortas;
- precalentar respuestas frecuentes;
- cachear audios de frases comunes;
- ajustar velocidad y pausas.

## Parametros de calidad

### Latencia objetivo

Para que parezca fluido:

- deteccion de fin de frase: 300-700 ms,
- STT de frase corta: menos de 1 s ideal,
- decision del agente: menos de 300 ms,
- TTS: menos de 1 s para frases cortas,
- respuesta total percibida: 1.5-2.5 s.

### Calidad de conversacion

El agente debe:

- hablar poco,
- confirmar datos criticos,
- no interrumpir de forma agresiva,
- admitir incertidumbre,
- ofrecer alternativas,
- cerrar con accion clara.

### Robustez

Casos que debe manejar desde el principio:

- ruido de restaurante,
- persona que cambia de idea,
- hora ambigua,
- nombre mal reconocido,
- llamada para cancelar,
- llamada para confirmar,
- cliente que pide algo fuera de reglas,
- baja confianza del STT.

## Integracion con RestaurIA

Nuevas entidades sugeridas:

```text
Reservation
  id
  customer_name
  phone
  party_size
  starts_at
  expected_duration_minutes
  table_id
  status
  source
  notes
```

```text
VoiceCall
  id
  started_at
  ended_at
  caller_phone
  intent
  outcome
  confidence
  escalated
```

```text
VoiceTurn
  id
  call_id
  speaker
  transcript
  intent
  confidence
  created_at
```

Eventos de dominio:

- `voice.call.started`
- `voice.intent.detected`
- `reservation.requested`
- `reservation.confirmed`
- `reservation.cancelled`
- `reservation.modified`
- `reservation.escalated`
- `voice.call.ended`

## Roadmap recomendado

### Sprint 1: simulador de llamada

- pantalla con boton de microfono,
- transcripcion local,
- respuesta por texto,
- crear reserva desde el dialogo.

### Sprint 2: TTS local

- integrar Piper,
- voz espanola,
- cache de frases comunes,
- control de velocidad y pausas.

### Sprint 3: motor de dialogo

- maquina de estados,
- intenciones basicas,
- confirmacion de datos,
- escalado al encargado.

### Sprint 4: disponibilidad conectada a sala

- reservas contra mesas reales,
- bloqueo de mesas,
- ETA de liberacion,
- rechazo educado si no hay disponibilidad fiable.

### Sprint 5: telefonia real opcional

- Asterisk en Linux/WSL/VM,
- ARI o modulo Vosk-Asterisk,
- prueba con extension VoIP local antes de una linea real.

## Bibliografia y documentacion legal

### Libros y PDFs directos

- Speech and Language Processing, Jurafsky & Martin: https://www.web.stanford.edu/~jurafsky/slp3/ed3book.pdf
- The Kaldi Speech Recognition Toolkit: https://danielpovey.com/files/2011_asru_kaldi.pdf
- Whisper paper: https://cdn.openai.com/papers/whisper.pdf
- VITS, base tecnica de muchos TTS neuronales: https://arxiv.org/pdf/2106.06103
- Rasa Open Source paper: https://arxiv.org/pdf/1712.05181
- Dialogue management survey: https://arxiv.org/pdf/2307.10897
- What Makes a Good Conversation?: https://arxiv.org/pdf/1901.06525
- Howl wake word toolkit: https://aclanthology.org/2020.nlposs-1.9.pdf
- dateparser PDF: https://dateparser.readthedocs.io/_/downloads/en/v1.3.0/pdf/
- Asterisk: The Definitive Guide, 5th Edition: https://files.phreaknet.org/asterisk5.pdf

Nota sobre Asterisk: el PDF enlazado indica licencia Creative Commons Attribution-NonCommercial-NoDerivatives 4.0. Es util para estudio/TFG no comercial, pero no debe modificarse ni redistribuirse como material propio.

### Documentacion tecnica

- Vosk API: https://github.com/alphacep/vosk-api
- Vosk Server: https://alphacephei.com/vosk/server
- Vosk Asterisk: https://github.com/alphacep/vosk-asterisk
- whisper.cpp: https://github.com/ggml-org/whisper.cpp
- whisper.cpp streaming: https://github.com/ggml-org/whisper.cpp/blob/master/examples/stream/README.md
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Piper TTS: https://github.com/rhasspy/piper
- Piper voices: https://github.com/rhasspy/piper/blob/master/VOICES.md
- Piper voices en Hugging Face: https://huggingface.co/rhasspy/piper-voices
- Silero VAD: https://github.com/snakers4/silero-vad
- openWakeWord: https://github.com/dscripka/openWakeWord
- Rasa Open Source: https://opensource.rasa.com/
- Rasa intents and entities: https://rasa.com/docs/reference/primitives/intents-and-entities/
- spaCy Spanish models: https://spacy.io/models/es/
- dateparser: https://dateparser.readthedocs.io/en/stable/
- Asterisk ARI: https://docs.asterisk.org/Configuration/Interfaces/Asterisk-REST-Interface-ARI/
- Asterisk External Media and ARI: https://docs.asterisk.org/Development/Reference-Information/Asterisk-Framework-and-API-Examples/External-Media-and-ARI/

### Privacidad y cumplimiento

- AEPD transcripcion de voz con IA: https://www.aepd.es/prensa-y-comunicacion/blog/transcripcion-de-voz-con-ai
- AEPD guia de videovigilancia: https://www.aepd.es/guias/guia-videovigilancia.pdf
- AEPD camaras en establecimientos publicos: https://www.aepd.es/sites/default/files/2021-02/fichas-videovigilancia-5-camaras-establecimientos-publicos.pdf

## Decision final

Para RestaurIA, la version con mayor valor y menor riesgo es:

```text
VAD: Silero o WebRTC VAD
STT: Vosk
NLU: reglas + dateparser
Dialogo: maquina de estados propia
TTS: Piper
Telefonia: navegador primero, Asterisk despues
LLM local: opcional, solo para reformular texto, nunca para decidir reservas
```

La inteligencia importante no esta en que el agente "hable mucho", sino en que solo prometa lo que el restaurante puede cumplir segun reservas, sala y carga operativa.
