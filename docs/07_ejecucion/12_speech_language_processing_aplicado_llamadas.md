# Speech and Language Processing aplicado a llamadas

Fuente analizada:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\ed3book.pdf
```

Libro:

```text
Speech and Language Processing, 3rd edition draft
```

## Partes del indice utiles para RestaurIA

El libro es demasiado amplio para aplicarlo entero. Para el agente telefonico interesan estas zonas:

- clasificacion de texto: detectar intencion de llamada,
- entidades y sequence labeling: extraer nombre, telefono, personas, fecha, hora,
- informacion, eventos y tiempo: normalizar fechas y rellenar plantillas,
- ASR: entender errores de transcripcion y medir WER en fases futuras,
- TTS: evaluar naturalidad y preparar texto antes de sintetizar,
- conversacion: turnos, actos de habla, grounding, subdialogos e iniciativa.

## Decision de producto

No se anade un LLM ni un clasificador pesado. Se aplica un enfoque determinista:

```text
transcript -> intent -> scenario -> slots -> action_name -> reply/escalado
```

La prioridad es evitar respuestas inventadas. Si el agente no dispone de informacion fiable, deriva al encargado.

## Casuisticas de llamada cubiertas

Se anade un catalogo inicial de escenarios:

- alergias o restricciones alimentarias,
- queja o reclamacion,
- evento privado o celebracion,
- aviso de retraso,
- horario o cocina abierta,
- carta, menu o precios,
- direccion o como llegar,
- aparcamiento,
- terraza o zona concreta,
- accesibilidad,
- mascotas,
- ninos, tronas o carritos,
- para llevar o delivery,
- objeto perdido,
- proveedor o factura,
- trabajo o curriculum,
- lista de espera.

## Implementacion aplicada

Nuevo modulo:

```text
services/voice/scenarios.py
```

Cada escenario define:

- `scenario_id`,
- intencion amplia,
- etiqueta humana,
- palabras clave,
- texto de respuesta,
- riesgo,
- si interrumpe una reserva,
- si requiere encargado.

Ejemplo:

```text
Cliente: Queria reservar para 2, soy celiaco.
Agente:
  intent = special_request
  scenario_id = allergens
  action_name = action_escalate_to_manager
```

## Razonamiento aplicado

### Clasificacion

La llamada se clasifica antes de responder. Esto evita que preguntas de horario, proveedores o alergias caigan en `unknown`.

### Slot filling

Las reservas siguen rellenando slots:

- personas,
- fecha,
- hora,
- nombre,
- telefono.

Si falta algo, el agente pregunta solo ese dato.

### Grounding

El agente confirma solo cuando tiene datos suficientes. Si el usuario da una fecha incompleta, pregunta la hora. Si el caso es sensible, no improvisa.

### Actos de habla

Cada respuesta produce una accion estructurada:

```text
utter_ask_requested_time
action_confirm_reservation
action_escalate_to_manager
```

Esto permite que frontend, Asterisk o TTS reaccionen sin leer texto libre.

## Casos que deben escalar

Escalar siempre:

- alergias,
- quejas,
- eventos privados,
- accesibilidad,
- retraso sobre reserva,
- grupos especiales,
- informacion no configurada,
- baja confianza de ASR,
- cualquier conflicto de disponibilidad.

## Que queda para mas adelante

- medir `word error rate` cuando haya STT real,
- construir dataset de llamadas reales anonimizadas,
- entrenar clasificador ligero si las reglas dejan de ser suficientes,
- configurar informacion real del restaurante para responder horarios/carta sin encargado,
- convertir escenarios en politicas editables desde frontend.
