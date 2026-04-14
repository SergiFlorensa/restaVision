# Licencias y decisiones de stack

## Objetivo
Mantener el proyecto lo más open source y reutilizable posible.

## Herramientas claramente alineadas
- Python: documentación y ecosistema abiertos — https://docs.python.org/
- OpenCV — https://docs.opencv.org/4.x/d0/d3d/tutorial_general_install.html
- PyTorch — https://pytorch.org/get-started/locally/
- FastAPI — https://fastapi.tiangolo.com/
- PostgreSQL — https://www.postgresql.org/docs/
- Grafana OSS — https://grafana.com/oss/
- Vosk — Apache-2.0 — https://github.com/alphacep/vosk-api
- whisper.cpp — MIT — https://github.com/ggml-org/whisper.cpp

## Herramientas a vigilar

### Toolchain de Hailo (si se usa Hailo-8L)
Puede aportar ventajas claras de rendimiento/watt en edge, pero hay que revisar con detalle términos de SDK, drivers y redistribución antes de uso comercial.

### Ultralytics YOLO
Muy útil, pero con AGPL-3.0 para su edición open source.  
Si el proyecto se comercializa de forma cerrada, hay que revisar cuidadosamente esa implicación.  
- licencia: https://www.ultralytics.com/license
- docs: https://docs.ultralytics.com/

### Docker Desktop
Puede usarse gratis en personal/educación y pequeñas empresas dentro de ciertos límites; si el proyecto pasa a uso profesional mayor, hay que revisar la suscripción.  
- pricing: https://www.docker.com/pricing/
- licencia Desktop: https://docs.docker.com/subscription/desktop-license/

## Política recomendada
- prototipado rápido permitido,
- documentar toda decisión de licencia,
- antes de vender: auditoría completa del stack y dependencias.
