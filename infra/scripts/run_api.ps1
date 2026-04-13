$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    throw "No existe .venv. Ejecuta primero infra/scripts/setup_local.ps1"
}

.\.venv\Scripts\uvicorn apps.api.main:app --reload

