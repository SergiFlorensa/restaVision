# Fases del proyecto

## Fase 0 - Preparacion
Objetivo:
- definir alcance,
- elegir stack,
- preparar entorno,
- fijar arquitectura minima,
- fijar configuracion de copiloto operativo.

Entregables:
- documentacion base,
- estructura de repositorio,
- backlog inicial,
- plan de datos,
- plan legal basico,
- especificacion de Next Best Action y Promise Engine.

## Fase 1 - Laboratorio domestico con 1 mesa
Objetivo:
- demostrar que la cadena completa funciona en pequeno.

Capacidades:
- deteccion o entrada manual de ocupacion,
- conteo,
- mesa libre / ocupada,
- cronometro por sesion,
- guardado de eventos.

## Fase 2 - Estados de mesa y eventos
Objetivo:
- pasar de "veo personas" a "entiendo el ciclo de una mesa".

Capacidades:
- estados basicos de mesa,
- cambios de fase,
- tiempo medio por sesion,
- mesa finalizando,
- mesa pendiente de limpieza,
- trazabilidad temporal.

## Fase 3 - Cola y promesas
Objetivo:
- gestionar grupos en espera y comunicar tiempos realistas.

Capacidades:
- cola manual asistida,
- compatibilidad mesa-grupo,
- ETA baseline,
- Promise Engine,
- promesa en riesgo.

## Fase 4 - Motor de decision
Objetivo:
- convertir estado operativo en recomendaciones accionables.

Capacidades:
- Restaurant Pressure Index,
- Table Opportunity Score,
- Next Best Action,
- prioridades P1/P2/P3,
- decisiones peligrosas basicas.

## Fase 5 - Dashboard operativo
Objetivo:
- validar una pantalla util para servicio real.

Capacidades:
- accion principal,
- top 3 acciones,
- mapa simple de mesas,
- Modo Servicio Critico,
- modo tecnico separado.

## Fase 6 - Piloto pequeno real
Objetivo:
- validar con 1-2 mesas o una zona real del restaurante.

Capacidades:
- camara fija real,
- eventos reales,
- dashboard estable,
- recogida de feedback,
- analisis post-servicio basico.

## Fase 7 - Escalado
Objetivo:
- adaptar el sistema a mas camaras, mesas e integraciones.

Capacidades:
- zonas de interes por mesa,
- arquitectura edge mas robusta,
- monitorizacion,
- integracion con reservas, TPV/POS o KDS,
- operacion diaria.
