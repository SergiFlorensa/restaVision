# Programas, paquetes y dependencias

## Programas base
- Python 3.x
- Git
- VS Code o IDE equivalente
- PostgreSQL
- navegador moderno
- Docker/Podman opcional

## Paquetes Python mínimos
- opencv-python
- numpy
- pandas
- pydantic
- fastapi
- uvicorn
- sqlalchemy
- psycopg
- scikit-learn
- matplotlib
- python-dotenv

## Paquetes ML / DL
- torch
- torchvision
- torchaudio (solo si aporta)
- ultralytics (solo si se acepta su licencia para prototipo)
- onnx / onnxruntime (si se exportan modelos)
- openvino (si se usa optimización Intel)

## Paquetes de ingeniería
- pytest
- black
- ruff
- mypy
- pre-commit
- alembic

## Paquetes opcionales de audio
- vosk
- pywhispercpp o bindings equivalentes
- sounddevice / pyaudio según enfoque

## Recomendación
Mantener separados:
- requirements/base.txt
- requirements/dev.txt
- requirements/ml.txt
- requirements/audio.txt
