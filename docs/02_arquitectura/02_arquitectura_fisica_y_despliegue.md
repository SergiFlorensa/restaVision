# Arquitectura física y despliegue

## Etapa 1 — MVP doméstico
Componentes:
- 1 ordenador principal,
- 1 webcam,
- backend local,
- base de datos local,
- dashboard local.

Ventajas:
- coste mínimo,
- latencia baja,
- fácil depuración.

## Etapa 2 — Piloto 1–2 mesas
Componentes:
- 1–2 cámaras,
- PC o mini PC dedicado,
- backend local,
- red local,
- dashboard web.

## Etapa 3 — Piloto real pequeño
Componentes:
- cámaras fijas en zonas definidas,
- edge compute dedicado,
- base de datos estable,
- monitorización.

## Etapa 4 — Escalado real
Componentes:
- varias cámaras,
- procesamiento por zonas o pipelines,
- mayor observabilidad,
- posible cluster ligero o separación por servicios.

## Enfoque de despliegue
### Preferido
- inferencia local,
- almacenamiento local o híbrido,
- API local con FastAPI,
- Postgres local,
- dashboard local o intranet.

### Motivos
- privacidad,
- latencia,
- menor coste recurrente,
- independencia de nube.

## Optimizaciones
- OpenVINO para hardware Intel/open source edge: https://docs.openvino.ai/
- Jetson si se requiere edge GPU dedicado: https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/

## Nota de diseño
Para el TFG, la arquitectura debe poder funcionar sin Internet una vez instalado el stack base.
