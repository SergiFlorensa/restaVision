# AGENTS.md

## Contexto del proyecto
RestaurIA es un TFG con vocación de evolucionar a producto real: un copiloto visual y predictivo para la gestión de sala en restaurantes, con enfoque local-first, modular y escalable.

## Reglas de trabajo
- La documentación funcional y de arquitectura se mantiene en español.
- Antes de implementar, revisar `docs/00_overview/04_documento_maestro_de_arranque.md`.
- Mantener la separación por capas: `apps/`, `services/`, `data/`, `models/`, `infra/`.
- No versionar datos reales, vídeos, pesos de modelos, secretos ni artefactos pesados.
- Cualquier nueva dependencia debe revisarse contra `docs/04_software_y_devops/05_licencias_y_decisiones_de_stack.md`.
- Priorizar primero el MVP: una cámara, una mesa, eventos, sesiones, dashboard mínimo y ETA baseline.

## Prioridades inmediatas
1. Sustituir la persistencia en memoria por una capa real con SQLAlchemy y Postgres.
2. Añadir configuración editable de cámaras, zonas y mesas.
3. Implementar un adaptador de captura que convierta frames en observaciones del dominio.
4. Construir el primer dashboard operativo sobre la API local.
