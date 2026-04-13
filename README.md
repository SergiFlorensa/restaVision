# RestaurIA

RestaurIA es un proyecto de TFG orientado a construir un copiloto visual y predictivo para la gestión operativa de sala en restaurantes. El objetivo es empezar con un MVP local, medible y explicable, y dejar una base técnica que pueda escalar a piloto real y, si funciona, a producto comercial.

## Estado actual

El repositorio queda preparado en **Fase 0: Preparación**. Ya existe una base documental sólida y una estructura inicial profesional para empezar el desarrollo con orden, control de versiones y separación clara entre documentación, código, datos, modelos e infraestructura.

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
- [Fases del proyecto](docs/00_overview/02_fases_del_proyecto.md)
- [Estructura de repositorio](docs/04_software_y_devops/03_estructura_de_repositorio.md)
- [Setup local recomendado](docs/04_software_y_devops/04_setup_local.md)
- [Backlog inicial](docs/07_ejecucion/02_backlog_inicial.md)

## Convenciones iniciales

- Documentación y explicaciones en español.
- Código, nombres de módulos y convenciones técnicas en inglés cuando mejore la claridad.
- Datos brutos, clips, checkpoints y exportaciones pesadas no se versionan.
- El MVP debe funcionar sin depender de Internet una vez instalado el stack base.

## Siguientes pasos recomendados

1. Validar y afinar la especificación funcional del MVP ya existente.
2. Definir la máquina de estados de mesa.
3. Formalizar el diccionario de eventos.
4. Levantar la primera API local con endpoints de salud, cámaras, sesiones y eventos.
5. Implementar el pipeline mínimo `frame -> detección -> evento -> persistencia`.

## Licencia

La licencia del repositorio queda pendiente de decisión final. Antes de publicar una versión abierta o comercial conviene revisar `docs/04_software_y_devops/05_licencias_y_decisiones_de_stack.md`.
