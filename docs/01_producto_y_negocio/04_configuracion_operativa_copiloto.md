# Configuracion operativa del copiloto

## Decision de producto
RestaurIA pasa de ser un dashboard visual a ser un **copiloto operativo para restaurantes llenos**.

La vision queda fijada asi:

```text
RestaurIA filtra el caos de la sala, predice los proximos minutos y recomienda la siguiente mejor accion para reducir esperas, proteger el servicio y mejorar la rotacion.
```

La camara y la vision artificial son fuentes de evidencia. El producto no se vende por detectar mas objetos, sino por ayudar al encargado a decidir mejor bajo presion.

## Usuario principal
El usuario principal es el encargado, director de sala o host que opera en puerta y sala durante servicios con alta carga:
- sabado noche,
- cenas de empresa,
- navidad,
- verano,
- festivos,
- turnos con falta de personal.

El encargado sigue siendo el responsable de decidir, pero no es el unico receptor de la informacion. RestaurIA debe plantearse como un sistema de coordinacion de sala:
- panel compartido visible para encargado y equipo,
- acciones priorizadas para que todos entiendan la siguiente tarea,
- registro de quien atiende cada accion cuando se conozca,
- canal futuro de avisos por voz o pinganillo para trabajadores concretos.

El MVP no necesita comunicacion por voz real, pero la arquitectura ya debe diferenciar el canal de destino de cada accion:
- `shared_panel`: accion visible en pantalla,
- `earpiece`: aviso individual futuro,
- `manager_only`: decision reservada al encargado,
- `kitchen_or_bar`: posible integracion posterior.

## Pregunta central
El sistema debe responder en menos de cinco segundos:

```text
Y ahora que hago?
```

## Modos de uso

### Modo Operacion
Durante el servicio real. Debe ser simple, rapido y accionable.

Muestra:
- una accion principal,
- top 3 acciones,
- promesa de espera recomendada,
- mapa simple de mesas,
- alertas P1/P2.

No muestra:
- detecciones tecnicas,
- graficas densas,
- eventos menores,
- ruido visual que no derive en accion.

### Modo Servicio Critico
Variante del modo operacion para maxima presion.

Regla:

```text
Si una informacion no ayuda a actuar en menos de cinco segundos, no aparece.
```

Se activa por:
- ocupacion alta,
- cola activa,
- muchas mesas en estado finalizando o pendiente de limpieza,
- alertas P1 acumuladas,
- servicio especial o falta de personal.

### Modo Analisis
Despues del servicio.

Responde:
- donde se perdio tiempo,
- que mesas quedaron bloqueadas,
- que promesas de espera fallaron,
- que zona necesito apoyo,
- que se debe cambiar en el proximo servicio.

## Funcionalidades rectoras

### Next Best Action
Genera una recomendacion concreta:

```json
{
  "priority": "P1",
  "answer": "Preparar Mesa 12 para grupo de 4",
  "eta_minutes": 9,
  "confidence": 0.78,
  "reason": [
    "mesa compatible",
    "mesa finalizando",
    "cola activa",
    "tiempo superior a la media"
  ]
}
```

### Promise Engine
Calcula que espera se puede comunicar al cliente y alerta si la promesa esta en riesgo.

Ejemplos:
- "Ofrecer espera de 8-10 min al grupo de 4."
- "Promesa en riesgo: actualizar espera al grupo de entrada."

### Table Opportunity Score
Puntua que mesa conviene preparar o vigilar primero.

Senales:
- compatibilidad con grupos en cola,
- estado de finalizacion,
- platos retirados,
- tiempo de sesion,
- limpieza pendiente,
- capacidad de mesa.

### Restaurant Pressure Index
Mide presion operativa.

Variables:
- ocupacion,
- cola,
- ritmo de entradas,
- alertas P1,
- mesas finalizando,
- mesas pendientes de limpieza,
- mesas desatendidas,
- desviacion de esperas prometidas.

## Entradas minimas
- estado de mesas,
- fase operativa de cada mesa,
- ultimo momento de atencion,
- personal asignado cuando exista,
- sesiones activas,
- eventos por mesa,
- cola manual asistida,
- capacidad de mesa,
- ETA baseline,
- configuracion de zonas,
- feedback del encargado.

## Salidas minimas
- accion principal,
- top 3 acciones,
- acciones operativas registrables,
- prioridad P1/P2/P3,
- ETA o rango de espera,
- explicacion breve,
- canal recomendado de comunicacion,
- caducidad de la recomendacion,
- feedback aceptada/ignorada/incorrecta.

## Principio de diseno
La vision artificial no debe obligar al encargado a interpretar la pantalla. La interfaz debe traducir observaciones a decisiones.

```text
Observacion -> evento -> interpretacion -> prioridad -> recomendacion -> resultado
```

## Limites explicitos
No priorizar en el MVP:
- reconocimiento facial,
- edad o genero,
- audio conversacional,
- identificacion individual de camareros o clientes,
- acusaciones automaticas de impago,
- almacenamiento continuo de video,
- alertas sin accion clara.

## Metricas de valor
- error medio de ETA,
- promesas incumplidas,
- acciones recomendadas,
- acciones aceptadas,
- acciones utiles,
- tiempo hasta primera atencion,
- tiempo de cola,
- mesas bloqueadas detectadas,
- rotacion por mesa,
- reduccion de alertas irrelevantes.
