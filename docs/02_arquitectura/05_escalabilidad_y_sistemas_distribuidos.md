# Escalabilidad y sistemas distribuidos

## Propósito
Recoger los puntos aplicables del análisis sobre arquitectura web escalable, Git, nginx, SQLAlchemy, ZeroMQ, visualización y deep learning, traduciéndolos a decisiones útiles para RestaurIA.

La regla principal es mantener el MVP simple y local-first, pero construirlo de forma que pueda evolucionar a piloto real y producto sin reescribir el núcleo.

## Principio rector
RestaurIA debe escalar primero por **separación de responsabilidades**, no por infraestructura compleja.

Orden recomendado:
1. separar captura, percepción, eventos, estado, predicción y presentación,
2. persistir eventos y sesiones de forma fiable,
3. medir latencia y volumen real,
4. introducir colas o workers solo cuando exista presión operativa,
5. añadir proxy, balanceo o nodos distribuidos solo en piloto multi-cámara.

## Puntos a desarrollar con prioridad alta

### 1. Separación lectura/escritura
Idea extraída:
- las escrituras suelen ser más costosas que las lecturas,
- el dashboard no debe competir con el pipeline de captura por el mismo camino crítico.

Aplicación en RestaurIA:
- el endpoint de observaciones debe escribir eventos y actualizar estado,
- el dashboard debe leer snapshots ya preparados,
- las predicciones pesadas deben recalcularse por evento o por ventana temporal, no por frame.

Decisión:
- para MVP, basta con API síncrona y Postgres local,
- para piloto, preparar un worker que procese observaciones o predicciones fuera del hilo de petición.

### 2. Event log fiable
Idea extraída de Git:
- una historia compleja se entiende mejor como secuencia de objetos inmutables con identidad clara.

Aplicación en RestaurIA:
- `events` debe actuar como registro auditable,
- `sessions` agrega el ciclo operativo,
- `table_runtime` guarda el estado actual para consulta rápida.

Decisión:
- no convertir todavía el sistema en event sourcing completo,
- mantener los eventos como fuente de auditoría y entrenamiento futuro.

### 3. Unit of Work e Identity Map
Idea extraída de SQLAlchemy:
- una operación de negocio debe persistirse de forma consistente,
- una entidad cargada debe tener identidad clara dentro de la sesión de trabajo.

Aplicación en RestaurIA:
- procesar una observación implica actualizar runtime, sesión, eventos y predicción,
- esas piezas deben guardarse de forma coherente.

Estado actual:
- existe repositorio SQLAlchemy opcional,
- falta validar contra PostgreSQL real y endurecer transacciones por operación de dominio.

### 4. Asignación espacial robusta
Idea extraída de detección multiobjeto:
- IoU y NMS son piezas básicas para evitar duplicados y asignar detecciones a zonas.

Aplicación en RestaurIA:
- calcular solape entre detecciones y zonas,
- usar punto inferior central cuando el IoU no represente bien una persona sentada,
- aplicar NMS antes de generar conteos.

Estado actual:
- se añade `services/vision/geometry.py` con `BoundingBox`, IoU, asignación por zona y NMS.

## Puntos a desarrollar en fase intermedia

### 5. Colas y asincronía
Idea extraída:
- las colas desacoplan productores y consumidores,
- evitan que una tarea pesada bloquee una respuesta operativa.

Aplicación futura:
- cámara produce observaciones,
- worker de visión procesa frames,
- worker de predicción recalcula ETA,
- API y dashboard leen estado preparado.

Decisión:
- no introducir RabbitMQ, Kafka o ZeroMQ en el MVP,
- diseñar interfaces de servicio para que se puedan mover a workers después.

### 6. Cache de snapshots
Idea extraída:
- memoria y caché reducen lecturas repetidas y latencia.

Aplicación futura:
- cachear estado actual de sala,
- cachear features de ETA,
- cachear geometría de zonas.

Decisión:
- empezar con `table_runtime` en base de datos y memoria de proceso,
- estudiar caché externa solo si el dashboard o varias pantallas generan presión real.

### 7. Dashboard como capa desacoplada
Idea extraída de matplotlib:
- separar modelo visual, datos y superficie de renderizado.

Aplicación:
- el dashboard no debe contener lógica de negocio,
- cada mesa debe representarse desde un snapshot del backend,
- las pruebas visuales deben comprobar colores, posición y legibilidad.

Decisión:
- para aplicación operativa conviene priorizar frontend web simple o canvas/SVG,
- matplotlib puede servir para informes, prototipos o gráficos offline, no como UI principal si se necesita interactividad rica.

### 8. Nginx como frontera de despliegue
Idea extraída:
- nginx es útil como proxy inverso, terminación TLS y gestor de conexiones.

Aplicación futura:
- servir dashboard,
- proteger FastAPI,
- habilitar WebSockets,
- centralizar límites de tamaño y timeouts.

Decisión:
- no instalar nginx en laboratorio doméstico,
- añadirlo en piloto real o cuando haya acceso desde otros dispositivos del local.

### 9. ZeroMQ o mensajería ligera
Idea extraída:
- comunicación de baja latencia entre procesos sin broker central pesado.

Aplicación futura:
- cámara edge a servidor central,
- servidor a módulo de alertas,
- motor de reglas a pinganillo.

Decisión:
- no meter ZeroMQ antes de tener un pipeline de vídeo real,
- evaluar primero si basta con HTTP/WebSocket local.

## Puntos a dejar fuera del MVP

### Shared-nothing completo
Tiene sentido en sistemas distribuidos grandes, no en el laboratorio de una mesa.

Para RestaurIA:
- sí mantener módulos independientes,
- no distribuir estado entre nodos todavía.

### Balanceadores y múltiples nodos de IA
Solo son relevantes con:
- varias cámaras,
- inferencia pesada,
- hardware distribuido,
- o varias sedes.

### GRU/LSTM para ETA
Puede ser una evolución interesante, pero requiere histórico secuencial de calidad.

Antes:
- baseline estadístico,
- Random Forest o modelo clásico,
- métricas reales de error,
- dataset limpio por sesión.

### Detección de platos, billetes y datáfono
Puede mejorar el estado `finalizing` o `payment`, pero exige dataset y revisión legal/ética.

Antes:
- mesa libre/ocupada fiable,
- conteo estable,
- eventos persistidos,
- dashboard usable.

## Roadmap técnico derivado

### Ahora
- validar Postgres real,
- usar geometría de zonas para asignación espacial,
- crear adaptador de vídeo a observación,
- exponer snapshots útiles para dashboard.

### Después del primer pipeline de vídeo
- medir latencia por etapa,
- introducir NMS real sobre detecciones,
- calibrar umbrales de IoU y bottom-center,
- añadir métricas de falsos positivos por mesa.

### Piloto real
- nginx como proxy local,
- WebSocket para dashboard,
- worker de visión si la API se bloquea,
- política de retención de eventos y vídeos.

### Producto futuro
- multi-sede,
- cola de eventos robusta,
- workers por cámara,
- cache de snapshots,
- modelo predictivo secuencial si los datos lo justifican.

## Decisión profesional
La arquitectura escalable no debe ser una colección de tecnologías. Debe ser una secuencia de decisiones que reduzcan riesgo:
- primero modularidad,
- después datos fiables,
- después medición,
- después asincronía,
- después distribución.

RestaurIA debe demostrar excelencia técnica con un sistema pequeño que funciona bien, no con una infraestructura grande antes de tener carga real.
