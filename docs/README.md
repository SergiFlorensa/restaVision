# RestaurIA / Smart Restaurant AI — Carpeta maestra de documentación

Esta carpeta contiene la documentación inicial del proyecto de TFG orientado a crear un sistema open source de apoyo operacional para restaurantes mediante Computer Vision, Machine Learning, Deep Learning y software de decisión en tiempo real.

## Objetivo de esta carpeta
Tener, desde antes de arrancar el desarrollo, una base documental estructurada como en un proyecto serio:
- producto y problema de negocio,
- arquitectura técnica,
- estrategia de datos,
- stack open source,
- hardware y costes,
- legalidad y riesgos,
- roadmap y fases de ejecución.

## Filosofía del proyecto
1. **Open source primero**.
2. **Procesamiento local / edge primero**.
3. **MVP pequeño y medible**: casa → 1 mesa → 2 mesas → piloto real.
4. **Escalado gradual** solo cuando haya métricas y fiabilidad.
5. **IA útil, no decorativa**: todo módulo debe aportar utilidad operativa real.

## Índice
- `00_overview/` — visión global, alcance y fases.
- `01_producto_y_negocio/` — problema, propuesta de valor, KPIs y comercialización.
- `02_arquitectura/` — arquitectura lógica, física y de despliegue.
- `03_datos_y_ml/` — datos, etiquetas, ML, CV, DL, métricas.
- `04_software_y_devops/` — stack, dependencias, programas, instalación y operación.
- `05_hardware_y_costes/` — compras, niveles de hardware y presupuestos.
- `06_legal_y_riesgos/` — privacidad, videovigilancia, riesgos y mitigaciones.
- `07_ejecucion/` — roadmap, backlog, hitos y plan de validación.
- `08_referencias/` — fuentes, licencias y notas de decisión.

## Documento recomendado para arrancar
Antes de empezar a implementar, revisar:
- `00_overview/04_documento_maestro_de_arranque.md`

Ese documento consolida:
- el diagnóstico del estado actual,
- el alcance real del MVP,
- las decisiones estratégicas ya fijadas,
- el orden de ejecución recomendado,
- y los entregables mínimos previos a la implementación.

## Decisión estratégica inicial
El primer objetivo no es “controlar el 100% del restaurante”, sino construir un **copiloto de sala**:
- detecta estados de mesa,
- estima tiempos,
- predice liberación,
- detecta anomalías operativas,
- ayuda a decidir rápido al director o responsable de sala.

## Restricción principal
No depender de software caro ni de APIs de pago para el MVP. Solo se contemplan herramientas de pago si:
- el coste es bajo,
- aceleran mucho el trabajo,
- y dejan una base útil para escalar o vender.

## Referencias rápidas
- Python: https://docs.python.org/
- OpenCV: https://docs.opencv.org/4.x/d0/d3d/tutorial_general_install.html
- PyTorch: https://pytorch.org/get-started/locally/
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/
- Grafana OSS: https://grafana.com/oss/
- CVAT: https://docs.cvat.ai/
- Label Studio OSS: https://labelstud.io/label-studio-oss/
- OpenVINO: https://docs.openvino.ai/
- AEPD videovigilancia: https://www.aepd.es/guias/guia-videovigilancia.pdf
- EDPB vídeo y RGPD: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en
