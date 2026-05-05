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
- React — MIT — https://react.dev/
- Vite — MIT — https://vite.dev/
- TypeScript — Apache-2.0 — https://www.typescriptlang.org/
- lucide-react — ISC — https://lucide.dev/
- Vosk — Apache-2.0 — https://github.com/alphacep/vosk-api
- whisper.cpp — MIT — https://github.com/ggml-org/whisper.cpp

## Herramientas candidatas para agente de voz local
Referencia específica:
- `docs/07_ejecucion/07_agente_voz_reservas_stack_local.md`

Herramientas alineadas o candidatas:
- Piper TTS — motor local para voces `es_ES`. El paquete Python `piper-tts==1.4.2`
  instalado para Windows declara `GPL-3.0-or-later`; válido para TFG/demo local,
  pero antes de vender conviene revisar sustitución por binario/paquete con licencia
  adecuada o aislarlo como componente opcional. Las voces `rhasspy/piper-voices`
  deben revisarse por modelo antes de redistribuir — https://github.com/OHF-voice/piper1-gpl
- Kokoro ONNX — wrapper MIT y modelo Kokoro Apache-2.0; usar como TTS avanzado opcional local, con modelos en `models/checkpoints/` sin versionar — https://github.com/thewh1teagle/kokoro-onnx
- Silero VAD — MIT — https://github.com/snakers4/silero-vad
- Rasa Open Source — Apache-2.0 — https://github.com/RasaHQ/rasa
- dateparser — BSD — https://dateparser.readthedocs.io/
- spaCy — MIT; revisar licencia de cada modelo de idioma antes de uso comercial — https://spacy.io/
- Asterisk — GPL; recomendable solo para integracion telefonica avanzada, no para el MVP — https://docs.asterisk.org/

Decision actual:
- prototipo primero en navegador, sin telefonia real,
- Vosk como STT local inicial por streaming y bajo coste,
- Windows SAPI/Piper como fallback TTS local inicial y Kokoro ONNX como TTS avanzado para demo natural en CPU,
- reglas + `dateparser` para intenciones y fechas en el MVP,
- Rasa/spaCy/Duckling solo si las reglas dejan de ser suficientes,
- Asterisk como integracion avanzada y opcional, no como requisito del MVP.

## Decisión de frontend operativo
Para el dashboard local se adopta Vite + React + TypeScript con CSS propio y `lucide-react`.
La primera versión evita librerías pesadas de gráficas y renderiza la curva de cola con SVG nativo para reducir bundle y mantener fluidez en portátil básico.

## Herramientas a vigilar

### Toolchain de Hailo (si se usa Hailo-8L)
Puede aportar ventajas claras de rendimiento/watt en edge, pero hay que revisar con detalle términos de SDK, drivers y redistribución antes de uso comercial.

### Ultralytics YOLO
Muy útil, pero con AGPL-3.0 para su edición open source.  
Si el proyecto se comercializa de forma cerrada, hay que revisar cuidadosamente esa implicación.  
En el MVP se usa como dependencia de visión opcional para demos locales y detección de personas; no debe ocultarse esta restricción en una futura venta.  
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

## Decisión de lenguaje para visión
Referencia específica:
- `docs/04_software_y_devops/11_decision_python_vs_cpp_para_vision.md`

Decisión actual:
- Python como base del sistema,
- C++ solo como posible aceleración futura de módulos aislados si la latencia real lo exige.
