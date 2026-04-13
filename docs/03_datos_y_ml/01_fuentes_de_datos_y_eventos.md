# Fuentes de datos y eventos

## Fuente primaria
Vídeo de cámara(s).

## Fuente secundaria opcional
- eventos manuales,
- POS/TPV,
- reservas,
- sensores simples.

## Eventos mínimos del MVP
- persona_detectada,
- conteo_personas,
- entrada_a_mesa,
- salida_de_mesa,
- mesa_ocupada,
- mesa_liberada.

## Eventos fase 2
- inicio_sesion,
- cambio_estado_mesa,
- persona_sale_de_zona,
- mesa_pendiente_de_limpieza,
- mesa_lista.

## Eventos fase 3+
- posible_interaccion_de_pago,
- posible_anomalia,
- recomendacion_generada,
- alerta_emitida.

## Regla de oro
Primero construir un buen sistema de eventos. Sin eso, el ML acaba siendo frágil y opaco.
