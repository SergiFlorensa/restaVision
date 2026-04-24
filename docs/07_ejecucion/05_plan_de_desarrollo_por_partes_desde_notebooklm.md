# Plan de desarrollo por partes desde el historial de NotebookLM

## Propósito
Este documento convierte el historial importado desde NotebookLM en una hoja de ruta ejecutable para RestaurIA.

La conversación contiene ideas de arquitectura, visión artificial, proxémica, teoría de colas, edge AI, dashboard operativo y agente de voz. La decisión de proyecto es no intentar implementarlo todo a la vez, sino dividirlo en bloques que mantengan el MVP controlado y dejen camino hacia producto.

## Criterio rector
RestaurIA no debe perseguir "control total" como vigilancia invasiva. La interpretación correcta para el proyecto es **observabilidad operativa local**:
- entender mesas, zonas, tiempos y eventos,
- apoyar decisiones del responsable de sala,
- minimizar datos personales,
- evitar biometría e identificación individual,
- y mantener siempre una explicación trazable de cada recomendación.

## Síntesis de lo que aporta el historial

### 1. Máquinas de estados y especificación ejecutable
El análisis sobre FSM y StateWORKS refuerza una decisión central del proyecto: el comportamiento importante no debe quedar disperso en flags ni condicionales ocultos.

Aplicación directa:
- modelo explícito de estados de mesa,
- eventos con payload definido,
- trazabilidad de transiciones,
- tests de ciclo completo,
- separación entre flujo visual y lógica de negocio.

Ya está aplicado en:
- `services/events/state_machine.py`,
- `docs/02_arquitectura/04_modelo_de_estados_de_mesa.md`,
- `docs/03_datos_y_ml/08_diccionario_de_eventos_y_payloads.md`.

### 2. Proxémica y diseño de información bajo estrés
El análisis de Edward T. Hall no debe convertirse en reglas automáticas rígidas sobre personas. Su valor está en diseñar mejor la interfaz, las zonas y las alertas.

Aplicación directa:
- dashboard con información capturable de un vistazo,
- colores y estados operativos claros,
- evitar ruido visual,
- alertas suaves y no acusatorias,
- separación entre espacio físico, zona configurable y estado operativo.

Regla de diseño:
- una pantalla de sala debe ayudar a decidir en segundos, no obligar a interpretar texto largo.

### 3. OpenCV y pipeline visual
El bloque de OpenCV aporta el camino técnico para pasar de observaciones manuales a observaciones generadas por cámara.

Aplicación directa:
- captura desde archivo o cámara,
- definición de ROIs por mesa,
- preprocesado para reducir ruido,
- sustracción de fondo para ocupación inicial,
- homografía para vista cenital,
- tracking temporal para estabilidad.

Decisión:
- usar la API moderna de OpenCV (`cv2`) y `numpy`,
- no copiar literalmente la API antigua `CvCapture`/`IplImage`,
- mantener un adaptador `Video-to-Observation` desacoplado del dominio.

### 4. Machine Learning explicable
El historial insiste en patrones por tipo de grupo, día, hora, festivos y fase de servicio. Es una dirección correcta, pero solo después de persistir datos fiables.

Aplicación directa:
- empezar con ETA baseline por histórico,
- añadir variables simples antes de modelos complejos,
- priorizar modelos interpretables,
- medir MAE/RMSE de tiempo restante.

No debe hacerse todavía:
- segmentar edad o atributos sensibles,
- inferir perfiles personales,
- prometer precisión sin dataset propio.

### 5. Teoría de colas y capacidad
Little y Erlang aportan valor para capacidad global, pero no sustituyen la observación de una mesa concreta.

Aplicación directa:
- estimar presión de demanda,
- calcular tiempos de espera agregados,
- detectar saturación por franja,
- medir pérdida o demora de grupos sin reserva.

Regla:
- `ETA` responde por una mesa concreta,
- `teoría de colas` responde por la tensión del restaurante completo.

### 6. Edge AI y privacidad
El enfoque local-first aparece de forma recurrente y encaja con el producto:
- baja latencia,
- menor exposición de datos,
- funcionamiento sin nube,
- posibilidad de Raspberry Pi, mini PC, Jetson o Hailo-8L según fase.

Decisión:
- la aceleración hardware será opcional,
- el detector visual debe estar desacoplado,
- no se debe crear lock-in con un proveedor de NPU.

### 7. Dashboard, alertas y pinganillo
La idea del pinganillo es potente, pero pertenece a una fase posterior. Antes hacen falta datos, estados, dashboard y reglas estables.

Aplicación futura:
- notificaciones sonoras no invasivas,
- resumen por voz del estado de sala,
- entrada tipo "grupo de siete sin reserva",
- respuesta basada en estado real, ETA y capacidad.

Restricción:
- sin grabación continua innecesaria,
- sin audio cloud obligatorio,
- con VAD, cancelación de ruido y activación controlada.

## Desarrollo por partes

### Parte 1. Núcleo persistente y trazable
Objetivo:
- sustituir la memoria volátil por persistencia real para catálogo, runtime, sesiones, eventos y predicciones.

Estado:
- implementada una capa opcional SQLAlchemy activada por `ENABLE_POSTGRES=true`,
- el modo memoria sigue disponible por defecto,
- los tests verifican que el estado persiste entre instancias del servicio usando SQLAlchemy.

Criterio de cierre:
- API arranca con Postgres local,
- las tablas se crean automáticamente,
- una sesión creada antes de reiniciar la API sigue disponible después.

### Parte 2. Configuración editable de cámaras, zonas y mesas
Objetivo:
- dejar de depender del catálogo semilla fijo.

Estado:
- implementada una primera versión de endpoints para crear/actualizar cámaras, zonas y mesas,
- la geometría de zona se guarda como `polygon_definition`,
- la configuración se persiste mediante el repositorio SQLAlchemy cuando está activo.

Entregables:
- endpoints de listado y creación/actualización para cámaras,
- endpoints de listado y creación/actualización para zonas,
- endpoints de listado y creación/actualización para mesas,
- validación de capacidad y zona asociada,
- persistencia de la configuración.

Criterio de cierre:
- el usuario puede crear una mesa nueva sin tocar código,
- una zona queda asociada a una cámara y a una geometría,
- la API lista la configuración persistida tras reinicio.

### Parte 3. Adaptador de captura a observación
Objetivo:
- convertir vídeo en observaciones del dominio.

Entregables:
- lectura desde archivo y webcam,
- muestreo de FPS configurable,
- observaciones por zona,
- señales iniciales: `people_count_estimate`, `foreground_ratio`, `occupancy_score`,
- artefactos de depuración opcionales.
- asignación detección-zona con IoU o punto inferior central,
- limpieza de duplicados con NMS antes del conteo.

Criterio de cierre:
- una grabación de prueba genera observaciones repetibles,
- las observaciones alimentan la FSM sin cambios en la API de dominio.

Estado parcial:
- existe un adaptador detección-a-observación independiente de cámara,
- falta conectar OpenCV y un detector real de personas.

### Parte 4. Dashboard operativo mínimo
Objetivo:
- ofrecer una pantalla útil en momentos de presión.

Entregables:
- vista de mesas con estados,
- tiempo transcurrido,
- ETA baseline,
- eventos recientes,
- alerta de mesa pendiente de limpieza.

Criterio de cierre:
- un responsable puede responder "qué mesa se liberará antes" sin leer logs ni entrar en Swagger.

### Parte 5. Predicción y capacidad
Objetivo:
- pasar de una ETA por defecto a predicciones basadas en histórico.

Entregables:
- histórico por mesa,
- variables por franja, día y tamaño de grupo,
- baseline estadístico,
- primera comparación con modelo clásico,
- métricas de error.

Criterio de cierre:
- el sistema muestra ETA con explicación,
- se registra el error real al cerrar sesión,
- se puede comparar baseline contra modelo ML.

### Parte 6. Visión avanzada de fases y pago
Objetivo:
- detectar señales visuales que indiquen avance del servicio o cierre.

Entregables:
- eventos previstos como `payment_started`,
- detección experimental de datáfono, platos o gestos,
- dataset etiquetado propio,
- métricas de falsos positivos.

Criterio de cierre:
- la señal mejora el ETA o la priorización operativa,
- no introduce acusaciones ni decisiones automáticas sobre personas.

### Parte 7. Alertas suaves y agente de voz local
Objetivo:
- ayudar cuando el responsable no esté mirando la pantalla.

Estado parcial:
- existe un detector estadistico ligero para sesiones largas fuera de rango,
- las alertas se exponen por `GET /api/v1/alerts`,
- la alerta usa lenguaje operativo y no acusatorio,
- queda pendiente persistirlas y mostrarlas en dashboard.

Entregables:
- motor de alertas con prioridades,
- canal sonoro discreto,
- resumen por voz opcional,
- entrada de voz controlada para consultas simples.

Criterio de cierre:
- la alerta reduce tiempo de reacción sin aumentar ruido ni estrés,
- toda recomendación puede verse también en el dashboard.

### Parte 8. Piloto y endurecimiento de producto
Objetivo:
- pasar de laboratorio a restaurante real.

Entregables:
- instalación edge reproducible,
- calibración de cámara,
- políticas de retención,
- auditoría de licencias,
- documentación de operación,
- métricas de ROI.

Criterio de cierre:
- el sistema puede demostrar ahorro de tiempo, mejora de rotación o reducción de incertidumbre con datos medidos.

## Decisiones de prioridad

### Implementar ya
- persistencia SQLAlchemy/Postgres,
- configuración editable,
- adaptador de captura,
- dashboard mínimo.
- geometría base de visión: bounding boxes, IoU, NMS y asignación a zonas.
- alertas estadisticas suaves sobre duracion de sesion.

### Preparar pero no sobredimensionar
- homografía,
- background subtraction,
- tracking,
- ETA con histórico,
- métricas de capacidad.

### Aparcar hasta tener datos reales
- detección de datáfono,
- estimación de edad o perfil sensible,
- audio conversacional,
- agente LLM local,
- análisis avanzado de impago.

## Nuevos puntos desde anomalias estadisticas
La deteccion de anomalias se incorpora como apoyo operativo, no como sistema de acusacion.

Puntos aplicados:
- comparar la duracion activa contra historico de sesiones cerradas,
- exigir minimo de muestras antes de alertar,
- usar margen absoluto minimo para evitar fragilidad,
- devolver evidencia numerica trazable,
- emitir como maximo una alerta por sesion y tipo.

Puntos pospuestos:
- persistencia de alertas,
- segmentacion por franja horaria,
- modelos como Isolation Forest,
- deteccion automatica de impago.

Motivo:
- con una camara, una mesa y hardware normal, el valor inicial esta en detectar desviaciones temporales explicables y revisables por una persona.

## Nuevos puntos desde PRML
El material de Bishop se incorpora solo en piezas ligeras y defendibles para el MVP.

Puntos aplicados:
- matriz de perdida reutilizable para decisiones bajo incertidumbre,
- opcion de rechazo en la FSM para observaciones de baja confianza,
- evento `low_confidence_observation`,
- filtro de Kalman 2D para suavizar bounding boxes,
- PCA, whitening, correlacion y estadisticos suficientes para features tabulares,
- comite ponderado de posteriores para combinar reglas o modelos ligeros.

Puntos pospuestos:
- HMM completo de fases de comida,
- Viterbi para reconstruccion diaria,
- EM/Baum-Welch,
- Markov de orden superior,
- SVM/RVM,
- AdaBoost entrenado,
- kernels pesados.

Motivo:
- antes de inferir fases complejas hace falta una camara real, datos propios y metricas de ocupacion estables.

## Nuevos puntos desde proxemica
El material de Hall se incorpora como metricas operativas, no como interpretacion psicologica.

Puntos aplicados:
- clasificacion de distancias en bandas proxemicas,
- contactos staff-mesa,
- densidad operativa por zona,
- mensajes de voz prudentes,
- cooldown para evitar fatiga auditiva.

Puntos pospuestos:
- inferencia de postura, mirada o relacion entre personas,
- eventos sociales persistidos,
- perfiles culturales avanzados,
- agente de voz conversacional.

Motivo:
- las distancias solo son fiables tras calibrar la camara a metros reales, y cualquier lectura social debe seguir siendo medible, neutral y revisable.

## Nuevos puntos desde MLLM
El material multimodal se incorpora de forma pragmatica para hardware normal.

Puntos aplicados:
- parser ligero de instrucciones naturales para Maria,
- orquestador de doble velocidad para ejecutar analisis pesado solo por trigger,
- cooldown por motivo para controlar CPU/RAM,
- prompts operativos acotados y no invasivos.

Puntos pospuestos:
- VQA continuo sobre video en vivo,
- instruction tuning con dataset propio,
- RAG multimodal de manuales,
- agente conversacional completo.

Motivo:
- primero se prioriza estabilidad del pipeline de camara y control de recursos en portatil antes de ampliar capacidad linguistica.

## Siguiente paso inmediato
El siguiente bloque de desarrollo debe ser el **adaptador de captura a observación**. La configuración editable ya existe en una primera versión, así que el siguiente salto útil es generar observaciones desde vídeo real o grabado sin tener que introducirlas manualmente por API.

## Nuevos puntos desde arquitectura escalable
El análisis adicional sobre arquitectura web escalable añade una advertencia importante: no hay que confundir preparación para escalar con meter infraestructura antes de tiempo.

Puntos que sí se incorporan:
- separar escrituras del pipeline y lecturas del dashboard,
- preparar snapshots de estado para lectura rápida,
- mantener eventos como registro auditable,
- documentar el futuro uso de workers, WebSockets, nginx o mensajería ligera,
- usar IoU/NMS como pieza base del pipeline de visión.

Puntos que se posponen:
- ZeroMQ,
- nginx,
- shared-nothing real,
- balanceadores,
- GRU/LSTM,
- detección avanzada de objetos de pago.
- BERT/agente de voz,
- aprendizaje por refuerzo.

Motivo:
- primero hace falta un pipeline local fiable, medido y trazable.
