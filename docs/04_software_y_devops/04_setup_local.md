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
La API puede trabajar en dos modos:
- memoria local, por defecto, para pruebas rápidas,
- SQLAlchemy/PostgreSQL si `ENABLE_POSTGRES=true`.

Con PostgreSQL activo, el ORM crea las tablas mínimas al arrancar:
- `cameras`,
- `zones`,
- `tables`,
- `table_runtime`,
- `sessions`,
- `events`,
- `predictions`.

Referencia:
- `docs/03_datos_y_ml/02_esquema_de_datos.md`

## Paso 5 — Captura
Conectar webcam y guardar secuencias cortas.

Referencia técnica:
- `docs/04_software_y_devops/07_opencv_y_adapter_de_captura.md`

## Paso 6 — Primer pipeline
- frame → detección → conteo → evento → guardado.

## Paso 7 — Dashboard
Empezar simple:
- HTML mínimo,
- o Grafana si ya hay métricas estructuradas.

## Recomendación
El primer día no intentes contenedores, audio ni múltiples cámaras.
