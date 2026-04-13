# Setup local recomendado

## Paso 1 — Base
Instalar:
- Python — https://docs.python.org/
- PostgreSQL — https://www.postgresql.org/docs/
- Git
- OpenCV — https://docs.opencv.org/4.x/d0/d3d/tutorial_general_install.html
- PyTorch — https://pytorch.org/get-started/locally/

## Paso 2 — Entorno virtual
Crear entorno virtual y congelar dependencias por archivo.

## Paso 3 — Backend local
Levantar FastAPI y exponer endpoints básicos:
- health,
- camera status,
- sessions,
- events,
- predictions.

## Paso 4 — Base de datos
Crear tablas mínimas:
- tables,
- zones,
- sessions,
- events.

## Paso 5 — Captura
Conectar webcam y guardar secuencias cortas.

## Paso 6 — Primer pipeline
- frame → detección → conteo → evento → guardado.

## Paso 7 — Dashboard
Empezar simple:
- HTML mínimo,
- o Grafana si ya hay métricas estructuradas.

## Recomendación
El primer día no intentes contenedores, audio ni múltiples cámaras.
