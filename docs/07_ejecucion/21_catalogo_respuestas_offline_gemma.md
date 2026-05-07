# Catalogo de respuestas offline para agente de voz

## Decision
Gemma/Ollama no debe ir en el camino critico de una llamada si tarda varios segundos en CPU. La arquitectura recomendada es usarlo como herramienta offline para mejorar frases, y usar en directo un catalogo local por `action_name`.

## Fundamento tecnico
La literatura sobre sistemas de dialogo orientados a tareas separa:
- comprension de intencion y slots,
- politica de dialogo,
- generacion de respuesta.

El trabajo de Template Guided Text Generation propone convertir acciones estructuradas en plantillas y usar un modelo generativo para reescribirlas de forma natural. Para RestaurIA, se aplica sin entrenar: las plantillas son la fuente fiable y Gemma solo propone variantes offline.

La literatura de cache para LLM y asistentes de voz refuerza la misma idea: en sistemas sensibles a latencia se reutilizan respuestas frecuentes o se anticipan resultados, evitando invocar el modelo grande en cada turno.

## Implementacion aplicada
- `services/voice/reply_catalog.py`: catalogo versionado de respuestas por `action_name`.
- `VoiceReservationAgent`: usa el catalogo para preguntas, confirmaciones y escalados frecuentes.
- `tools/build_voice_reply_catalog.py`: exporta el catalogo y puede generar variantes offline con Ollama.
- `services/voice/response_compressor.py`: mantiene fast-path, cache y fallback si aun se usa Ollama.

## Uso sin Ollama
```bash
python tools/build_voice_reply_catalog.py
```

Genera:

```text
data/interim/voice_reply_catalog.generated.json
```

## Uso con Ollama offline
```bash
python tools/build_voice_reply_catalog.py --use-ollama --model gemma4:e2b-it-q4_K_M --timeout 20 --num-thread 4
```

Este comando no debe ejecutarse durante una llamada. Sirve para revisar variantes, elegir manualmente las mejores y, si son buenas, incorporarlas al catalogo.

## Regla de producto
En llamada:

```text
action_name + slots -> catalogo local -> TTS cacheado
```

Para peticiones complejas:

```text
turno complejo -> frase puente inmediata -> Gemma/Ollama en segundo plano -> respuesta si llega a tiempo
```

La frase puente puede incluir un recurso de espera no bloqueante:

```text
Entiendo. Lo compruebo un momento. Si quiere consultar la carta u otra informacion del restaurante, puede entrar en la web de La Piemontesa.
```

URL de referencia para mostrar en pantalla o documentacion:
- https://www.lapiemontesa.com/

En voz no conviene dictar la URL completa salvo que el cliente lo pida; es demasiado larga para una llamada.

Fuera de llamada:

```text
catalogo -> Gemma/Ollama -> revision humana -> catalogo local
```

## Criterios de aceptacion de una frase
- Conserva todos los slots obligatorios.
- No inventa disponibilidad ni decisiones.
- Suena natural en castellano de Espana.
- Tiene menos de 18-25 palabras si es pregunta simple.
- Es facil de entender por telefono.
- No requiere contexto oculto para entenderse.

## Fuentes
- Template Guided Text Generation for Task-Oriented Dialogue: https://aclanthology.org/2020.emnlp-main.527.pdf
- GPTCache, cache semantica para reducir latencia y coste: https://aclanthology.org/anthology-files/pdf/nlposs/2023.nlposs-1.24.pdf
- CHA, framework de cache edge para asistentes de voz: https://research.ibm.com/publications/cha-a-caching-framework-for-home-based-voice-assistant-systems
- Personalized predictive ASR for latency reduction in voice assistants: https://www.amazon.science/publications/personalized-predictive-asr-for-latency-reduction-in-voice-assistants
