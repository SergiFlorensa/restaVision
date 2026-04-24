# Stack recomendado

## Lenguaje principal
- Python — https://docs.python.org/

## Visión artificial
- OpenCV — https://docs.opencv.org/4.x/d0/d3d/tutorial_general_install.html
- PyTorch — https://pytorch.org/get-started/locally/

## API / backend
- FastAPI — https://fastapi.tiangolo.com/

## Base de datos
- PostgreSQL — https://www.postgresql.org/docs/

## Dashboards / observabilidad
- Grafana OSS — https://grafana.com/oss/

## Anotación
- CVAT — https://docs.cvat.ai/
- Label Studio OSS — https://labelstud.io/label-studio-oss/

## Voz local opcional
- Vosk (STT offline, Apache-2.0) — https://github.com/alphacep/vosk-api
- whisper.cpp (MIT) — https://github.com/ggml-org/whisper.cpp

## Aceleración de inferencia
- OpenVINO — https://docs.openvino.ai/
- HailoRT / toolchain Hailo (si se adopta NPU Hailo-8L como backend opcional de inferencia)

## Contenerización
- Docker / Docker Desktop (evaluar licencia y uso)
  - pricing: https://www.docker.com/pricing/
  - licencia Desktop: https://docs.docker.com/subscription/desktop-license/

## Recomendación oficial para este proyecto
### MVP
- Python + OpenCV + PyTorch + FastAPI + Postgres
- sin nube
- sin pago
- sin dependencia externa

Nota de decisión:
- mantener Python como lenguaje principal del proyecto; evaluar C++ solo para módulos concretos si el profiling real demuestra un cuello de botella.

### Piloto más serio
- añadir Grafana,
- añadir OpenVINO,
- contenerizar componentes.
