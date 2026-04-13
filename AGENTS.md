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
1. Validar y afinar la especificación funcional del MVP ya existente.
2. Formalizar estados de mesa y transiciones.
3. Definir diccionario de eventos y payloads.
4. Preparar el esqueleto técnico de API, persistencia y pipeline de captura.
