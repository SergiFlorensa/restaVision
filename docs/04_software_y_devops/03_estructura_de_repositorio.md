# Estructura de repositorio sugerida

```text
restauria/
|-- AGENTS.md
|-- docs/
|-- apps/
|   |-- api/
|   |-- dashboard/
|   `-- worker/
|-- services/
|   |-- vision/
|   |-- events/
|   |-- prediction/
|   |-- alerts/
|   |-- decision/
|   `-- decision_engine/
|-- models/
|   |-- checkpoints/
|   |-- exported/
|   `-- metadata/
|-- data/
|   |-- raw/
|   |-- interim/
|   |-- processed/
|   `-- annotations/
|-- infra/
|   |-- docker/
|   |-- scripts/
|   `-- db/
|-- tests/
|-- notebooks/
|-- requirements/
|-- pyproject.toml
|-- .editorconfig
|-- .gitattributes
|-- .gitignore
`-- README.md
```

## Separacion por capas
- `apps/api`: endpoints para estado, cola, decisiones y feedback.
- `apps/dashboard`: interfaz de Modo Operacion, Modo Servicio Critico y modo tecnico.
- `services/vision`: deteccion, tracking y observaciones visuales.
- `services/events`: eventos de dominio y bus de tiempo real.
- `services/prediction`: ETA baseline y modelos predictivos.
- `services/alerts`: alertas P1/P2/P3.
- `services/decision`: utilidades genericas de decision ya existentes.
- `services/decision_engine`: logica de producto operativo: presion, promesas, oportunidad y Next Best Action.
- `data`: datos de prueba, anonimizados o sinteticos.
- `models`: solo metadatos y artefactos ligeros versionables.
- `infra`: base de datos, despliegue y scripts de soporte.

## Regla
Separar claramente:
- codigo de inferencia,
- eventos de dominio,
- logica de negocio,
- motor de decision,
- dashboards,
- datos,
- experimentacion.

## Regla adicional
No versionar en Git:
- datos brutos reales,
- clips de video,
- checkpoints pesados,
- secretos o credenciales locales.
