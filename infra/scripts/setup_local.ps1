param(
    [switch]$InstallMl = $true
)

$ErrorActionPreference = "Stop"

Write-Host ">> Creando entorno virtual si no existe..."
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

Write-Host ">> Actualizando pip..."
.\.venv\Scripts\python -m pip install --upgrade pip

Write-Host ">> Instalando dependencias base y de desarrollo..."
.\.venv\Scripts\python -m pip install -r requirements\dev.txt

if ($InstallMl) {
    Write-Host ">> Instalando dependencias de vision y ML..."
    .\.venv\Scripts\python -m pip install -r requirements\ml.txt
}

Write-Host ">> Instalando hooks de pre-commit..."
.\.venv\Scripts\pre-commit install

Write-Host ">> Ejecutando tests..."
.\.venv\Scripts\python -m pytest -q

Write-Host ">> Setup local completado."

