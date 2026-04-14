# Integración sugerida de NPU Hailo-8L

## Objetivo
Aterrizar una vía de aceleración **local-first** para el pipeline de visión del MVP sin romper la arquitectura por capas.

## Qué aporta Hailo-8L al proyecto
- menor consumo energético frente a una GPU dedicada para inferencia continua,
- latencia estable para detección de personas en tiempo real,
- posibilidad de desplegar en mini-PC + acelerador edge,
- alineación con el objetivo de privacidad (inferencia local sin nube).

## Dónde encaja en RestaurIA
Encaja en la capa de **adaptadores de captura/inferencia** (`services/`) y no en la lógica de negocio (`apps/`).
La recomendación es mantener una interfaz común de inferencia para poder cambiar backend:
- backend CPU (baseline),
- backend OpenVINO (Intel),
- backend HailoRT (Hailo-8L),
- backend Jetson (si se migra a NVIDIA).

## Diseño recomendado (sin acoplar el dominio)
1. Definir contrato `DetectorBackend` con métodos mínimos:
   - `load_model()`
   - `infer(frame)`
   - `healthcheck()`
2. Implementar `HailoDetectorBackend` en `services/vision/`.
3. Normalizar salida de detección a un esquema único de observación del dominio.
4. Mantener reglas de estado/mesa independientes del hardware.

## Plan de adopción por fases
### Fase A — Validación técnica (rápida)
- usar el modelo actual en CPU como referencia,
- medir FPS, latencia p95 y consumo,
- repetir con backend Hailo-8L,
- aceptar solo si mejora material sin perder precisión operativa.

### Fase B — Integración MVP
- selector de backend por configuración (`.env` / YAML),
- métricas por backend en logs,
- fallback automático a CPU si falla el acelerador.

### Fase C — Piloto
- pruebas de estabilidad largas (jornadas de servicio),
- validación térmica y energética,
- checklist de recuperación ante reinicio del dispositivo.

## Métricas mínimas de decisión
- FPS medio y mínimo por cámara,
- latencia p50/p95 de inferencia,
- tasa de frames perdidos,
- consumo energético aproximado,
- impacto en precisión operacional (ocupada/libre, inicio/fin de sesión).

## Riesgos y mitigación
- **Riesgo de lock-in de SDK**: mitigar con interfaz de backend desacoplada.
- **Conversión/compatibilidad de modelos**: mantener baseline CPU funcional.
- **Complejidad operativa en despliegue**: automatizar instalación y healthcheck.

## Nota de licencias y distribución
Antes de distribución comercial:
- revisar licencia de runtime/SDK y redistribución de componentes de Hailo,
- documentar versión exacta de drivers y dependencias,
- validar compatibilidad con la política de licencias del stack.

## Recomendación práctica
Sí, es una integración interesante y relevante para vuestro objetivo.
La forma correcta de hacerlo es como **backend intercambiable de inferencia**, nunca como dependencia rígida del núcleo del dominio.
