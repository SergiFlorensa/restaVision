# RestaurIA / restaVision - Carpeta maestra de documentacion

Esta carpeta contiene la documentacion inicial del proyecto de TFG orientado a crear un **copiloto operativo de sala** para restaurantes.

El objetivo no es construir solo un dashboard con camara. El objetivo es ayudar al encargado o director de sala a decidir mejor en momentos de alta presion.

## Objetivo de esta carpeta
Tener una base documental estructurada como en un proyecto serio:
- producto y problema de negocio,
- configuracion operativa del copiloto,
- arquitectura tecnica,
- estrategia de datos,
- stack open source,
- hardware y costes,
- legalidad y riesgos,
- roadmap y fases de ejecucion.

## Filosofia del proyecto
1. **Utilidad operativa primero**.
2. **Procesamiento local / edge primero**.
3. **MVP pequeno y medible**: casa -> 1 mesa -> 2 mesas -> piloto real.
4. **Decision accionable por encima de dashboard saturado**.
5. **Escalado gradual** solo cuando haya metricas y fiabilidad.
6. **IA util, no decorativa**: todo modulo debe aportar utilidad operativa real.

## Indice
- `00_overview/` - vision global, alcance y fases.
- `01_producto_y_negocio/` - problema, propuesta de valor, KPIs, MVP y configuracion operativa.
- `02_arquitectura/` - arquitectura logica, fisica y de despliegue.
- `03_datos_y_ml/` - datos, etiquetas, ML, CV, DL, metricas y motor de decision.
- `04_software_y_devops/` - stack, dependencias, programas, instalacion y operacion.
- `05_hardware_y_costes/` - compras, niveles de hardware y presupuestos.
- `06_legal_y_riesgos/` - privacidad, videovigilancia, riesgos y mitigaciones.
- `07_ejecucion/` - roadmap, backlog, hitos y plan de validacion.
- `08_referencias/` - fuentes, licencias y notas de decision.

## Documentos recomendados para arrancar
Antes de implementar, revisar:
- `00_overview/04_documento_maestro_de_arranque.md`
- `01_producto_y_negocio/04_configuracion_operativa_copiloto.md`
- `01_producto_y_negocio/03_especificacion_funcional_mvp.md`
- `03_datos_y_ml/06_iea_y_motor_de_decision.md`

## Decision estrategica vigente
RestaurIA debe responder:

```text
Y ahora que hago?
```

El primer objetivo es construir un sistema que:
- detecta o registra estados de mesa,
- estima tiempos,
- gestiona cola manual asistida,
- recomienda esperas prometibles,
- genera Next Best Action,
- prioriza alertas P1/P2/P3,
- aprende con feedback de recomendaciones.

## Restriccion principal
No depender de software caro ni de APIs de pago para el MVP. Solo se contemplan herramientas de pago si:
- el coste es bajo,
- aceleran mucho el trabajo,
- y dejan una base util para escalar o vender.

## Referencias rapidas
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
- EDPB video y RGPD: https://www.edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-32019-processing-personal-data-through-video_en
