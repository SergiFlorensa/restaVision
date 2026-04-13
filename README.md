# RestaurIA

RestaurIA es un proyecto de TFG orientado a construir un copiloto visual y predictivo para la gestión operativa de sala en restaurantes. El objetivo es empezar con un MVP local, medible y explicable, y dejar una base técnica que pueda escalar a piloto real y, si funciona, a producto comercial.

## Estado actual

El repositorio queda preparado para cerrar **Fase 0** y entrar en la primera implementación del MVP. Ya existe una base documental sólida, una estructura profesional de repositorio y un núcleo técnico ejecutable para empezar a iterar con criterio.

## Objetivo del MVP

El primer alcance del sistema es:
- detectar si una mesa está libre u ocupada,
- estimar cuántas personas hay en la mesa,
- registrar sesiones y eventos operativos,
- mostrar un dashboard mínimo,
- ofrecer una primera ETA de liberación con lógica interpretable.

## Estructura del repositorio

```text
restauria/
├─ AGENTS.md
├─ apps/
├─ data/
├─ docs/
├─ infra/
├─ models/
├─ notebooks/
├─ requirements/
├─ services/
├─ tests/
├─ .editorconfig
├─ .gitattributes
├─ .gitignore
├─ pyproject.toml
└─ README.md
```

## Documentación clave

- [Documento maestro de arranque](docs/00_overview/04_documento_maestro_de_arranque.md)
- [Visión general del proyecto](docs/00_overview/01_vision_general.md)
- [Especificación funcional del MVP](docs/01_producto_y_negocio/03_especificacion_funcional_mvp.md)
- [Modelo de estados de mesa](docs/02_arquitectura/04_modelo_de_estados_de_mesa.md)
- [Diccionario de eventos y payloads](docs/03_datos_y_ml/08_diccionario_de_eventos_y_payloads.md)
- [Fases del proyecto](docs/00_overview/02_fases_del_proyecto.md)
- [Estructura de repositorio](docs/04_software_y_devops/03_estructura_de_repositorio.md)
- [Setup local recomendado](docs/04_software_y_devops/04_setup_local.md)
- [Instalación gratuita y configuración local](docs/04_software_y_devops/06_instalacion_gratuita_y_configuracion_local.md)
- [Backlog inicial](docs/07_ejecucion/02_backlog_inicial.md)

## Convenciones iniciales

- Documentación y explicaciones en español.
- Código, nombres de módulos y convenciones técnicas en inglés cuando mejore la claridad.
- Datos brutos, clips, checkpoints y exportaciones pesadas no se versionan.
- El MVP debe funcionar sin depender de Internet una vez instalado el stack base.

## Arranque rápido

1. Crear entorno virtual.
2. Ejecutar `.\infra\scripts\setup_local.ps1`.
3. Copiar `.env.example` a `.env` cuando se vaya a activar PostgreSQL.
4. Levantar la API local con `.\infra\scripts\run_api.ps1`.
4. Abrir `http://127.0.0.1:8000/docs` para probar el MVP.

## Qué ya existe en código

- API local mínima con FastAPI.
- Catálogo semilla con una cámara, una zona y una mesa.
- Máquina de estados de mesa del MVP.
- Generación de eventos operativos.
- Gestión de sesiones de mesa.
- ETA baseline simple basada en histórico.
- Tests automáticos del flujo principal.

## Siguientes pasos recomendados

1. Añadir persistencia real con SQLAlchemy y Postgres para sesiones, eventos y predicciones.
2. Modelar configuración editable de cámaras, zonas y mesas.
3. Implementar el adaptador de captura para pasar de observaciones manuales a observaciones generadas desde vídeo.
4. Levantar un dashboard mínimo que consuma la API local.
5. Medir precisión de ocupación, latencia y error medio de ETA en pruebas controladas.

## Licencia

La licencia del repositorio queda pendiente de decisión final. Antes de publicar una versión abierta o comercial conviene revisar `docs/04_software_y_devops/05_licencias_y_decisiones_de_stack.md`.
