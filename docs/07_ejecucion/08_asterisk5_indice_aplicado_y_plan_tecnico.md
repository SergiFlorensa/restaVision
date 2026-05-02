# Asterisk 5 aplicado a RestaurIA

Fuente analizada:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\asterisk5.pdf
```

Libro:

```text
Asterisk: The Definitive Guide, 5th Edition
```

## Lectura del indice

El libro cubre una centralita Asterisk completa, pero RestaurIA no necesita aplicar todo de golpe. Para el TFG y el MVP, solo interesan los bloques que permiten recibir una llamada, conducir una conversacion corta, registrar la decision y conectar la telefonia con el backend.

## Capitulos utiles para RestaurIA

### Prioridad alta

#### Capitulo 14: Automated Attendant

Utilidad:

- disenar saludo inicial,
- separar operadora automatica de IVR,
- definir timeout e input invalido,
- evitar conversaciones largas sin objetivo.

Aplicacion en RestaurIA:

- guion inicial del agente,
- politicas de escalado al encargado,
- respuestas cortas y controladas.

#### Capitulo 16: Interactive Voice Response

Utilidad:

- estructura de IVR,
- llamadas hacia servicios externos,
- bases para speech recognition y TTS.

Aplicacion en RestaurIA:

- el agente de reservas se comporta como IVR inteligente,
- cada turno de voz produce una intencion,
- el backend decide si acepta, rechaza o escala.

#### Capitulo 18: AGI

Utilidad:

- enviar llamadas desde Asterisk a un programa externo,
- FastAGI como puente TCP,
- separar logica telefonica de logica de negocio.

Aplicacion en RestaurIA:

- Asterisk no debe decidir reservas;
- Asterisk debe enviar audio/transcripcion/eventos;
- RestaurIA debe decidir disponibilidad y respuesta.

#### Capitulo 19: ARI

Utilidad:

- control moderno de llamadas por REST/WebSocket,
- arquitectura orientada a aplicaciones externas,
- puente natural con servicios Python.

Aplicacion en RestaurIA:

- fase avanzada para controlar llamada real,
- eventos de llamada hacia FastAPI,
- integracion limpia con agente de voz.

#### Capitulo 21: Monitoring and Logging

Utilidad:

- registros de llamada,
- CDR,
- eventos de canal,
- trazabilidad tecnica.

Aplicacion en RestaurIA:

- guardar call_id, intent, outcome y escalado;
- no guardar audio real por defecto;
- medir latencia por turno.

#### Capitulo 22: Security

Utilidad:

- proteger APIs de red,
- evitar credenciales debiles,
- limitar exposicion de Asterisk.

Aplicacion en RestaurIA:

- Asterisk solo en local/red controlada en TFG;
- no exponer AMI/ARI a Internet;
- secretos fuera del repositorio.

### Prioridad media

#### Capitulo 5: User Device Configuration

Sirve cuando se pruebe con softphone o extension VoIP local.

#### Capitulo 6: Dialplan Basics

Sirve para crear el flujo minimo:

```text
entrante -> saludo -> agente RestaurIA -> encargado si falla
```

#### Capitulo 7: Outside Connectivity

Importante solo si se conecta una linea real o proveedor SIP. Fuera del MVP inicial.

#### Capitulo 15: Database Integration

No es prioritario porque RestaurIA ya usa PostgreSQL/FastAPI. Asterisk no debe escribir reservas directamente en base de datos.

#### Capitulo 20: WebRTC

Interesante para fase futura si se quiere llamar desde navegador como telefono.

## Decision tecnica

No se instala Asterisk todavia.

Primero se implementa una capa propia de agente de llamadas en RestaurIA:

```text
canal de llamada
  -> transcript STT
  -> POST /api/v1/voice/calls/{call_id}/turns
  -> agente de reservas
  -> disponibilidad contra mesas reales
  -> respuesta controlada
  -> TTS o Asterisk Playback
```

Esto permite que el mismo agente funcione con:

- simulador en navegador,
- pruebas manuales desde Swagger,
- futura integracion con Vosk/Piper,
- futura integracion con Asterisk AGI/ARI.

## Implementacion realizada en esta fase

Se anade el primer nucleo software:

```text
services/voice/
```

Capacidades:

- crear sesion de llamada,
- recibir turnos de texto transcrito,
- detectar intencion basica en espanol,
- extraer personas, hora, nombre y telefono,
- consultar disponibilidad contra mesas del MVP,
- confirmar reserva si hay mesa lista,
- rechazar si no hay disponibilidad fiable,
- cancelar reserva por telefono o nombre,
- escalar por baja confianza o caso ambiguo.

Endpoints:

```text
POST /api/v1/voice/calls
GET  /api/v1/voice/calls
GET  /api/v1/voice/calls/{call_id}
POST /api/v1/voice/calls/{call_id}/turns
GET  /api/v1/voice/reservations
```

## Primer guion operativo

Entrada:

```text
Queria reservar mesa para 4 a las 21:30 a nombre de Sergio, mi telefono es 600123123
```

Salida esperada:

```text
Reserva confirmada para 4 personas a las 21:30, a nombre de Sergio. Gracias.
```

Si no hay mesa lista:

```text
Ahora mismo no puedo garantizar esa mesa. Puedo dejar aviso al encargado o buscar otra hora.
```

Si la transcripcion es poco fiable:

```text
No he entendido la llamada con suficiente claridad. Le paso con el encargado.
```

## Siguiente paso recomendado

La siguiente iteracion debe implementar el simulador visual de llamada:

- boton de iniciar llamada,
- caja con transcripcion,
- respuesta del agente,
- estado de reserva,
- latencia por turno,
- boton para simular baja confianza,
- boton para escalar al encargado.

Despues:

1. Vosk como STT local.
2. Piper como TTS local.
3. WebSocket de audio.
4. Asterisk con AGI/ARI solo cuando el flujo de negocio ya sea estable.
