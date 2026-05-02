# KPIs y metricas de negocio

## KPIs operativos
- tiempo medio de espera prometido vs real,
- error medio de ETA de liberacion,
- tiempo medio de limpieza y reasignacion,
- tiempo hasta primera atencion,
- tiempo de reaccion del responsable ante P1,
- porcentaje de recomendaciones ejecutadas.

## KPIs de decision
- acciones recomendadas por servicio,
- acciones aceptadas,
- acciones marcadas como utiles,
- recomendaciones caducadas,
- decisiones peligrosas evitadas,
- precision de prioridad P1/P2,
- tasa de alertas sin accion clara.

## KPIs de eficiencia
- rotacion de mesas por franja,
- covers por servicio,
- tiempo improductivo entre salida y siguiente ocupacion,
- numero de grupos rechazados innecesariamente,
- carga ofrecida por franja (`erlangs`),
- probabilidad estimada de saturacion o bloqueo,
- capacidad activa efectiva por zona.

## KPIs de experiencia
- reduccion de esperas exageradas o falsas expectativas,
- consistencia en tiempos prometidos,
- promesas de espera incumplidas,
- abandono de cola,
- disminucion de conflictos por cola.

## KPIs de riesgo operativo
- mesas bloqueadas detectadas,
- mesas desatendidas detectadas,
- promesas en riesgo,
- alertas P1/P2 por turno,
- falsos positivos,
- casos confirmados relevantes.

## KPIs tecnicos
- FPS efectivos por camara,
- latencia media por evento,
- latencia media hasta recomendacion,
- disponibilidad del sistema,
- uso de CPU/GPU,
- tasa de error por modulo.

## Regla clave
No escalar un modulo si antes no mejora un KPI real.

La precision visual importa, pero no es suficiente. El exito del producto se mide por mejores decisiones, menos esperas mal prometidas y menos ruido durante el servicio.
