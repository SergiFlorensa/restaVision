# Maria: flujo de doble velocidad

## Proposito
Definir como integrar analisis multimodal de forma viable en un portatil normal con camara IP tipica.

La clave es no ejecutar analisis pesado en cada frame. Se combina:
- flujo rapido y continuo para deteccion operativa,
- flujo pesado y puntual para razonamiento visual-lenguaje.

## Principio de diseno
Arquitectura de doble velocidad:

```text
Flujo A (rapido):
  camara -> deteccion/tracking -> eventos/estado/alertas

Flujo B (puntual):
  trigger -> captura puntual -> analisis multimodal -> resumen/accion
```

El Flujo B solo se activa cuando hay valor operacional real.

## Implementacion actual
Codigo:
- `services/maria/instructions.py`
- `services/maria/orchestrator.py`

Tests:
- `tests/test_maria_instructions.py`
- `tests/test_maria_orchestrator.py`

## Parser de instrucciones
`MariaInstructionParser` traduce ordenes de texto a intentos estructurados:
- `room_summary`,
- `table_attention`,
- `table_cleanliness`,
- `zone_crowding`,
- `proximity_review`,
- `generic_review`.

Tambien extrae:
- `table_id` desde frases tipo "mesa 4",
- pista de zona (`barra`, `entrada`, `terraza`, ...).

Objetivo:
- evitar logica ad hoc de prompts,
- estandarizar entrada del operador,
- preparar futura integracion con LLM local.

## Orquestador de triggers
`MariaOrchestrator` decide si lanzar analisis pesado segun:
- consulta explicita del operador,
- evento de baja confianza,
- transiciones relevantes de mesa,
- alertas operativas warning,
- congestion alta de zona,
- resumen periodico con cooldown.

No dispara siempre: aplica cooldown por motivo para controlar CPU/RAM.

## Motivos de trigger
Motivos actuales:
- `operator_query`
- `low_confidence`
- `table_transition`
- `operational_alert`
- `crowding_high`
- `periodic_summary`

Cada motivo tiene cooldown independiente configurable en `MariaOrchestratorConfig`.

## Prompt operacional
El orquestador genera prompts acotados a accion de sala:
- confirmar estado coherente de mesa,
- validar alerta de sesion larga,
- revisar congestion de zona,
- resumir estado general para el operador.

No se incluyen tareas sensibles:
- inferir emociones,
- identificar personas,
- clasificar intenciones personales.

## Integracion futura
Cuando exista modelo local (por ejemplo via Ollama):
1. parser extrae intent y contexto,
2. orquestador decide si ejecutar,
3. se toma captura puntual,
4. se llama al modelo multimodal local,
5. se convierte la salida en mensaje operativo breve.

## Que se pospone
Se pospone en esta fase:
- VQA completo continuo sobre video,
- instruction tuning con dataset propio,
- RAG multimodal con manuales,
- cuantizacion avanzada y benchmark por hardware concreto.

Motivo:
- primero hay que cerrar pipeline de camara y calibracion basica,
- el TFG necesita estabilidad operativa antes de ampliar complejidad.

## Criterio profesional
El modulo Maria actual no intenta "hablar por hablar".
Solo prepara una capa de decision para ejecutar analisis pesado de forma controlada, medible y compatible con hardware normal.
