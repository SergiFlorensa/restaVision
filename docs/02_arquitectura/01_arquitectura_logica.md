# Arquitectura lógica

## Vista por capas

### Capa 1 — Captura
Entradas:
- cámaras USB o IP,
- posibles eventos manuales,
- más adelante POS / reservas.

Salida:
- stream de vídeo o frames,
- timestamps.

### Capa 2 — Percepción visual
Funciones:
- detección de personas,
- tracking,
- detección de ocupación,
- clasificación de zonas,
- eventos visuales relevantes.

Salida:
- observaciones estructuradas.

### Capa 3 — Motor de eventos
Convierte señales visuales en eventos de negocio:
- mesa_ocupada,
- mesa_liberada,
- persona_se_levanta,
- grupo_entrante,
- posible_pago,
- salida_de_zona,
- mesa_en_limpieza.

### Capa 4 — Estado operacional
Mantiene el estado actual de cada mesa:
- libre,
- ocupada,
- comiendo,
- finalizando,
- pago,
- vacía pendiente de limpieza,
- lista.

### Capa 5 — Analítica / ML
Calcula:
- duraciones,
- medias,
- ETA,
- scores,
- anomalías.

### Capa 6 — Reglas / decisión
Ejemplos:
- priorizar mesas a revisar,
- sugerir asignación,
- marcar riesgo,
- elevar alertas.

### Capa 7 — Presentación
- dashboard,
- logs,
- alertas suaves,
- notificaciones opcionales.

## Principios de arquitectura
- desacoplamiento entre percepción y negocio,
- persistencia de eventos,
- explicabilidad,
- posibilidad de simulación y replay,
- edge-first.
