# Evaluacion del agente de voz con corpus baseline

## Origen tecnico

Fuente aplicada:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\ed3book.pdf
```

Partes usadas:

- clasificacion y metricas de precision, recall y F1,
- entidades y slot filling,
- normalizacion temporal,
- grounding y estructura conversacional,
- evaluacion ASR como fase posterior con WER.

## Decision implementada

Se incorpora una evaluacion reproducible del agente de voz antes de conectar telefonia real.

El objetivo no es que el agente parezca inteligente, sino medir si convierte una llamada en:

- intencion correcta,
- accion correcta,
- slots correctos,
- campos pendientes correctos,
- escenario sensible correcto,
- escalado correcto.

## Modulos anadidos

```text
services/voice/evaluation.py
tools/evaluate_voice_agent.py
```

Endpoint:

```text
GET /api/v1/voice/evaluation/baseline
```

## Corpus inicial

El corpus baseline cubre:

- reserva completa,
- reserva con hora relativa en lenguaje natural,
- fecha parcial que obliga a pedir hora,
- consulta de disponibilidad,
- cancelacion sin identificador,
- alergia que interrumpe una reserva,
- horario sin base de conocimiento configurada,
- reclamacion,
- baja confianza STT,
- solicitud directa de encargado.

## Metricas expuestas

El reporte devuelve:

- `intent_accuracy`,
- `intent_macro_precision`,
- `intent_macro_recall`,
- `intent_macro_f1`,
- `action_accuracy`,
- `call_status_accuracy`,
- `scenario_accuracy`,
- `missing_fields_accuracy`,
- `slot_exact_match_rate`,
- `slot_field_accuracy`,
- `escalation_accuracy`,
- matriz de confusion por intencion,
- detalle por caso.

## Uso local

Desde terminal:

```powershell
python tools/evaluate_voice_agent.py
```

Guardar reporte:

```powershell
python tools/evaluate_voice_agent.py --output data/processed/voice_eval_baseline.json
```

## Criterio de aceptacion

Antes de conectar Asterisk, STT real o TTS, el agente debe mantener:

- `intent_accuracy >= 0.90`,
- `intent_macro_f1 >= 0.90`,
- `action_accuracy >= 0.90`,
- `slot_field_accuracy >= 0.90`,
- `escalation_accuracy = 1.00` en escenarios sensibles.

## Siguiente mejora logica

Convertir el corpus sintetico en un dataset anonimo con llamadas reales o simuladas por un encargado de sala. Cada nueva incidencia debe entrar primero como caso de evaluacion y despues como mejora de reglas, slots o politica de escalado.
