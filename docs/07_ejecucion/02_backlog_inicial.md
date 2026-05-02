# Backlog inicial

## Epica 1 - Captura y observacion
- [ ] Conectar webcam
- [ ] Capturar stream estable
- [ ] Guardar clips de prueba
- [ ] Permitir entrada manual alternativa de ocupacion para pruebas sin camara

## Epica 2 - Deteccion
- [ ] Detectar personas
- [ ] Contar personas
- [ ] Dibujar bounding boxes en modo tecnico
- [ ] Convertir detecciones a observaciones de dominio

## Epica 2.1 - Geometria de vision
- [x] Implementar bounding boxes e IoU
- [x] Implementar asignacion deteccion-zona por IoU
- [x] Implementar asignacion por punto inferior central
- [x] Implementar NMS basico
- [x] Anadir suavizado Kalman de bounding boxes
- [x] Integrar geometria en adaptador deteccion-a-observacion
- [x] Anadir suavizado temporal de conteo
- [ ] Conectar adaptador a captura OpenCV real

## Epica 3 - Logica de mesa
- [ ] Definir zona de mesa
- [ ] Marcar `ready` / `occupied`
- [ ] Detectar `finalizing`
- [ ] Detectar `pending_cleaning`
- [ ] Detectar `blocked`
- [ ] Detectar `needs_attention`
- [ ] Iniciar y cerrar sesiones
- [x] Rechazar transiciones de baja confianza
- [x] Registrar evento `low_confidence_observation`

## Epica 4 - Datos
- [x] Anadir repositorio SQLAlchemy opcional
- [x] Persistir eventos con ORM
- [x] Persistir sesiones con ORM
- [x] Persistir predicciones con ORM
- [ ] Validar `ENABLE_POSTGRES=true` contra PostgreSQL local
- [ ] Persistir `queue_groups`
- [ ] Persistir `decision_recommendations`
- [ ] Persistir `decision_feedback`
- [ ] Persistir alertas P1/P2 si el dashboard necesita historico auditable
- [ ] Exportar CSV de analisis

## Epica 4.1 - Configuracion operativa
- [x] Crear camaras desde API
- [x] Crear zonas desde API
- [x] Crear mesas desde API
- [x] Persistir geometria de zona
- [x] Validar capacidad y asociacion mesa-zona
- [ ] Configurar capacidades utiles para compatibilidad mesa-grupo
- [ ] Configurar modo de servicio: normal, busy, critical_service

## Epica 5 - Cola manual asistida
- [ ] Crear grupo en cola con tamano y hora de llegada
- [ ] Editar promesa de espera
- [ ] Asociar grupo a mesa candidata
- [ ] Marcar grupo sentado
- [ ] Marcar abandono de cola
- [ ] Calcular espera real

## Epica 6 - Prediccion y promesa
- [ ] Media por sesion
- [ ] ETA baseline
- [ ] Intervalo de confianza simple
- [ ] Promise Engine inicial
- [ ] Detectar promesa en riesgo
- [x] Anadir PCA y whitening para features tabulares
- [x] Anadir estadisticos suficientes incrementales
- [x] Anadir matriz de correlacion robusta
- [ ] Aplicar estas features a un dataset real de sesiones

## Epica 7 - Motor de decision
- [x] Crear detector estadistico ligero para sesiones largas
- [x] Exponer alertas operativas desde la API
- [x] Evitar duplicar alertas de la misma sesion
- [x] Crear matriz de perdida reutilizable para decisiones
- [x] Implementar opcion de rechazo por confianza
- [x] Crear comite ponderado de posteriores
- [ ] Crear `services/decision_engine/pressure_index.py`
- [ ] Crear `services/decision_engine/table_opportunity_score.py`
- [ ] Crear `services/decision_engine/promise_engine.py`
- [ ] Crear `services/decision_engine/next_best_action.py`
- [ ] Crear `services/decision_engine/decision_explainer.py`
- [ ] Crear `services/decision_engine/feedback_recorder.py`
- [ ] Endpoint `GET /api/v1/decisions/next-best-action`
- [ ] Endpoint `POST /api/v1/decisions/{id}/feedback`

## Epica 8 - Dashboard operativo
- [ ] Mostrar accion principal
- [ ] Mostrar top 3 acciones
- [ ] Mostrar promesa de espera recomendada
- [ ] Mostrar mapa simple de mesas
- [ ] Mostrar solo P1/P2 en modo servicio
- [ ] Crear Modo Servicio Critico
- [ ] Mantener modo tecnico separado para depuracion visual

## Epica 9 - Analisis post-servicio
- [ ] Resumen de picos de presion
- [ ] Mesas bloqueadas
- [ ] Promesas incumplidas
- [ ] Tiempo medio de primera atencion
- [ ] Recomendaciones para el siguiente servicio

## Epica 10 - Maria local (multimodal)
- [x] Parser de instrucciones naturales a intents operativos
- [x] Orquestador de triggers con cooldown por motivo
- [x] Prompts operativos acotados por tipo de trigger
- [ ] Conectar orquestador a recomendaciones del motor de decision
- [ ] Integrar con modelo local cuantizado (Ollama/GGUF)
- [ ] Medir latencia, RAM y tasa de activacion de analisis pesado
