# Estructura de repositorio sugerida

```text
restauria/
├─ AGENTS.md
├─ docs/
├─ apps/
│  ├─ api/
│  ├─ dashboard/
│  └─ worker/
├─ services/
│  ├─ vision/
│  ├─ events/
│  ├─ prediction/
│  └─ alerts/
├─ models/
│  ├─ checkpoints/
│  ├─ exported/
│  └─ metadata/
├─ data/
│  ├─ raw/
│  ├─ interim/
│  ├─ processed/
│  └─ annotations/
├─ infra/
│  ├─ docker/
│  ├─ scripts/
│  └─ db/
├─ tests/
├─ notebooks/
├─ requirements/
├─ pyproject.toml
├─ .editorconfig
├─ .gitattributes
├─ .gitignore
└─ README.md
```

## Regla
Separar claramente:
- código de inferencia,
- lógica de negocio,
- dashboards,
- datos,
- experimentación.

## Regla adicional
No versionar en Git:
- datos brutos reales,
- clips de vídeo,
- checkpoints pesados,
- secretos o credenciales locales.
