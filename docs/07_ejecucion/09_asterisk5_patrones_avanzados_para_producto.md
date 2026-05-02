# Patrones avanzados extraidos de Asterisk para RestaurIA

Fuente base:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\asterisk5.pdf
```

Este documento no propone montar una centralita completa en el MVP. Extrae patrones de Asterisk que pueden convertir RestaurIA en un producto mas serio: llamadas, reservas, sala, colas, trazabilidad y escalado.

## Idea rectora

El agente telefonico de RestaurIA no debe ser solo una voz que contesta. Debe actuar como un filtro operativo:

```text
llamada entrante
  -> entender motivo
  -> comprobar sala/reservas/capacidad
  -> resolver si puede
  -> escalar si hay riesgo
  -> dejar trazabilidad
```

## 1. Operadora automatica minima

Inspirado en el capitulo de automated attendant.

Aplicacion:

- saludo corto,
- detectar motivo,
- evitar menus largos,
- timeout claro,
- respuesta invalida controlada,
- transferencia al encargado si no entiende.

Valor diferencial:

- reduce interrupciones al encargado,
- no frustra al cliente con menus pesados,
- mantiene tono profesional.

Implementacion futura:

```text
VoiceCall.status = open | collecting_details | confirmed | rejected | escalated | closed
```

## 2. IVR inteligente conectado a sala

Inspirado en el capitulo de IVR.

Aplicacion:

- el IVR no pregunta opciones fijas,
- pregunta solo el dato que falta,
- llama al motor de disponibilidad,
- confirma o rechaza con criterio operativo.

Ejemplo:

```text
Cliente: mesa para 4 a las 21:30
Sistema: mira reservas, mesas, cola, ETA y carga
Respuesta: confirma, ofrece alternativa o escala
```

Valor diferencial:

- el agente promete solo lo que el restaurante puede cumplir.

## 3. FastAGI como puente futuro

Inspirado en AGI/FastAGI.

Aplicacion:

- Asterisk recibe la llamada,
- RestaurIA decide,
- Asterisk solo reproduce audio, espera entrada y transfiere.

Principio:

```text
La logica de negocio no vive en el dialplan.
```

Valor diferencial:

- el sistema se puede probar primero sin telefonia real,
- luego Asterisk se acopla como canal externo.

## 4. ARI como modo avanzado de control

Inspirado en ARI, Stasis y WebSocket.

Aplicacion futura:

- recibir eventos de llamada en tiempo real,
- pausar/reproducir audios,
- transferir al encargado,
- registrar estados,
- controlar la llamada desde FastAPI.

Uso recomendado:

- no usar ARI en el primer prototipo,
- usarlo cuando ya funcionen STT, TTS y dialogo.

## 5. Cola telefonica como sensor de saturacion

Inspirado en ACD queues.

Aplicacion:

- llamadas esperando,
- llamadas abandonadas,
- tiempo medio antes de responder,
- llamadas escaladas,
- llamadas resueltas por el agente.

Traduccion a RestaurIA:

```text
si hay muchas llamadas + cola fisica + sala llena
  -> activar modo servicio critico
  -> agente no acepta reservas dudosas
  -> solo confirma huecos muy seguros
```

Valor diferencial:

- la telefonia se convierte en una senal mas del estado operativo del restaurante.

## 6. Overflow operativo

Inspirado en overflow de colas.

Aplicacion:

- si el agente no puede resolver,
- si la confianza es baja,
- si el grupo es grande,
- si hay conflicto de disponibilidad,
- si el cliente insiste,
- si hay queja,

entonces:

```text
escalar al encargado
crear accion operativa
mostrar aviso en panel
```

Valor diferencial:

- el agente no se vuelve peligroso,
- el encargado solo recibe llamadas que merecen intervencion humana.

## 7. Call detail records para producto

Inspirado en CDR y logging.

Aplicacion:

- guardar llamada,
- intencion,
- resultado,
- duracion,
- escalado,
- reserva creada/cancelada,
- confianza media,
- motivo de rechazo.

No guardar por defecto:

- audio real,
- datos innecesarios,
- transcripciones sensibles largas.

Valor diferencial:

- dashboard post-servicio:
  - cuantas llamadas llegaron,
  - cuantas resolvio la IA,
  - cuantas reservas genero,
  - cuantas se perdieron,
  - cuando se satura el telefono.

## 8. Prompt engineering telefonico

Inspirado en prompts, timeout e invalid input.

Reglas:

- frases de menos de 2 lineas,
- una pregunta por turno,
- confirmar datos criticos,
- no explicar tecnologia,
- no prometer sin disponibilidad,
- repetir solo el dato dudoso.

Ejemplo malo:

```text
Estoy procesando la informacion de disponibilidad de nuestras mesas...
```

Ejemplo bueno:

```text
Para cuantas personas seria?
```

## 9. Seguridad desde el primer diseno

Inspirado en el capitulo de seguridad.

Reglas:

- no exponer Asterisk a Internet durante el TFG,
- ARI/AMI solo en localhost o red privada,
- usuarios no numericos,
- secretos fuera del repositorio,
- validar cualquier extension o numero,
- evitar que el usuario controle rutas internas.

Valor diferencial:

- el proyecto nace preparado para una demo seria sin riesgos evidentes.

## 10. Modo horario y politica del restaurante

Inspirado en dialplan con condiciones.

Aplicacion:

- horario de cocina,
- margen antes de cierre,
- maximo grupo automatico,
- bloqueo de reservas en servicio critico,
- dias especiales,
- politicas del encargado.

Ejemplo:

```text
si faltan menos de 40 min para cierre de cocina
  -> no aceptar nueva reserva sin encargado
```

## Prioridad de implementacion

### Implementado

Primer nucleo de `RestaurIA Voice Gatekeeper`:

- estado operativo del gatekeeper,
- modo `normal`, `guarded` o `critical`,
- score de presion telefonica/sala,
- proteccion de cola fisica cuando la sala esta cargada,
- overflow al encargado si una reserva telefonica puede perjudicar la operacion,
- metricas de llamadas,
- ratio de resolucion automatica,
- ratio de escalado,
- reservas confirmadas/canceladas.

Endpoints:

```text
GET /api/v1/voice/gatekeeper/status
GET /api/v1/voice/metrics
```

### Siguiente bloque recomendado

1. Simulador visual de llamada en frontend.
2. Motor editable de politicas del restaurante.
3. Piper para respuestas habladas.
4. Vosk para transcripcion local.
5. Asterisk con FastAGI/ARI.

## Feature distintiva para vender el proyecto

Nombre funcional:

```text
RestaurIA Voice Gatekeeper
```

Descripcion:

```text
Un agente telefonico que filtra llamadas, crea reservas y protege la sala de promesas imposibles usando el estado real del restaurante.
```

Esta es la diferencia frente a un bot generico: RestaurIA no solo habla, decide con informacion operativa.
