# Backlog inicial

## Épica 1 — Captura
- [ ] Conectar webcam
- [ ] Capturar stream estable
- [ ] Guardar clips de prueba

## Épica 2 — Detección
- [ ] Detectar personas
- [ ] Contar personas
- [ ] Dibujar bounding boxes

## Épica 2.1 — Geometría de visión
- [x] Implementar bounding boxes e IoU
- [x] Implementar asignación detección-zona por IoU
- [x] Implementar asignación por punto inferior central
- [x] Implementar NMS básico
- [x] Añadir suavizado Kalman de bounding boxes
- [x] Integrar geometría en adaptador detección-a-observación
- [x] Añadir suavizado temporal de conteo
- [ ] Conectar adaptador a captura OpenCV real

## Épica 2.2 — Pipeline cámara única
- [ ] Capturar frames con OpenCV
- [ ] Ejecutar detector ligero de personas
- [ ] Convertir detecciones a `ScoredDetection`
- [ ] Generar `TableObservation` automáticamente
- [ ] Enviar observaciones al motor de eventos
- [ ] Calibrar coordenadas de suelo para medir metros reales

## Épica 2.3 — Proxémica operativa
- [x] Clasificar distancias en bandas proxémicas
- [x] Calcular contactos staff-mesa
- [x] Calcular densidad operativa por zona
- [x] Generar avisos de voz prudentes
- [x] Limitar repetición de avisos por cooldown
- [ ] Integrar métricas proxémicas con dashboard tras calibrar cámara

## Épica 3 — Lógica de mesa
- [ ] Definir zona de mesa
- [ ] Marcar libre / ocupada
- [ ] Iniciar y cerrar sesiones
- [x] Rechazar transiciones de baja confianza
- [x] Registrar evento `low_confidence_observation`

## Épica 4 — Datos
- [x] Añadir repositorio SQLAlchemy opcional
- [x] Persistir eventos con ORM
- [x] Persistir sesiones con ORM
- [x] Persistir predicciones con ORM
- [ ] Validar `ENABLE_POSTGRES=true` contra PostgreSQL local
- [ ] Exportar CSV de análisis

## Épica 4.1 — Configuración operativa
- [x] Crear cámaras desde API
- [x] Crear zonas desde API
- [x] Crear mesas desde API
- [x] Persistir geometría de zona
- [x] Validar capacidad y asociación mesa-zona

## Épica 5 — Dashboard
- [ ] Mostrar estado actual
- [ ] Mostrar tiempo transcurrido
- [ ] Mostrar historial simple

## Épica 6 — Predicción
- [ ] Media por sesión
- [ ] ETA baseline
- [ ] Intervalo de confianza simple
- [x] Añadir PCA y whitening para features tabulares
- [x] Añadir estadísticos suficientes incrementales
- [x] Añadir matriz de correlación robusta
- [ ] Aplicar estas features a un dataset real de sesiones

## Épica 7 — Riesgo
- [x] Crear detector estadistico ligero para sesiones largas
- [x] Exponer alertas operativas desde la API
- [x] Evitar duplicar alertas de la misma sesion
- [x] Crear matriz de perdida reutilizable para decisiones
- [x] Implementar opcion de rechazo por confianza
- [x] Crear comite ponderado de posteriores
- [ ] Persistir alertas si el dashboard lo necesita
- [ ] Medir falsos positivos con pruebas controladas
- [ ] Detectar salida escalonada solo como senal operativa
- [ ] Detectar falta de senal de cierre
- [ ] Score simple de anomalia por franja horaria
- [ ] Validar que las senales proxemicas no generan alertas invasivas

## Épica 8 — María local (multimodal)
- [x] Parser de instrucciones naturales a intents operativos
- [x] Orquestador de triggers con cooldown por motivo
- [x] Prompts operativos acotados por tipo de trigger
- [ ] Conectar orquestador a capturas reales de cámara
- [ ] Integrar con modelo local cuantizado (Ollama/GGUF)
- [ ] Medir latencia, RAM y tasa de activación de análisis pesado
