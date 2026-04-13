# Documento maestro de arranque

## Propósito
Este documento convierte la documentación existente en un marco de ejecución profesional. Su función es alinear tres horizontes que no deben confundirse:
- el **TFG** como trabajo académico serio y demostrable,
- el **MVP** como sistema mínimo operativo validable,
- el **producto escalable** como posible solución comercial futura.

## Diagnóstico inicial

### Lo que ya está bien definido
- existe un problema real y valioso: reducir incertidumbre operativa en sala,
- el MVP está correctamente acotado a ocupación, tiempos, eventos y dashboard,
- la arquitectura está pensada por capas y con separación entre visión, eventos y negocio,
- la estrategia edge-first está alineada con privacidad, latencia y coste,
- la documentación ya contempla riesgos legales, métricas y evolución por fases.

### Lo que falta para pasar de “idea sólida” a “proyecto ejecutable”
- una **especificación funcional formal del MVP**,
- una **máquina de estados de mesa** con reglas de transición explícitas,
- un **diccionario de eventos** con entradas, salidas y payloads definidos,
- criterios de validación cuantificados por módulo,
- una estrategia clara para aislar dependencias con posible impacto de licencia,
- una estructura real de repositorio y trabajo técnico reproducible.

## Objetivo rector del proyecto
Construir un **copiloto operacional de sala** que, a partir de vídeo local, sea capaz de:
- detectar si una mesa está libre u ocupada,
- estimar cuántas personas hay en la mesa,
- registrar sesiones y eventos operativos,
- mostrar el estado actual y el tiempo acumulado,
- ofrecer una primera estimación de liberación de mesa con lógica interpretable.

## Qué significa “éxito” en cada horizonte

### TFG
Éxito significa:
- demostrar un problema relevante,
- justificar técnicamente la solución,
- implementar una cadena funcional mínima,
- medir resultados,
- documentar limitaciones, riesgos y decisiones.

### MVP
Éxito significa:
- una mesa,
- una cámara,
- un pipeline estable,
- persistencia de eventos y sesiones,
- dashboard operativo,
- pruebas repetibles en entorno controlado.

### Producto escalable
Éxito significa:
- varias mesas y zonas,
- múltiples cámaras,
- observabilidad,
- despliegue edge repetible,
- auditoría legal y de licencias,
- capacidad de vender, mantener y evolucionar el sistema.

## Decisiones estratégicas que conviene fijar desde ya
- **Local-first**: el MVP debe funcionar sin depender de Internet.
- **Un solo caso de uso principal**: el núcleo inicial es la gestión de estado y liberación de mesas.
- **Baselines antes que complejidad**: primero reglas, estadística y ML clásico; después DL temporal si demuestra valor.
- **Privacidad por diseño**: sin reconocimiento facial, sin identificación nominal y sin inferencias sensibles.
- **Abstracción del detector visual**: el sistema debe desacoplar el motor de detección para poder cambiarlo en el futuro sin rehacer la lógica de negocio.

## Alcance recomendado del MVP

### Dentro del alcance
- captura desde webcam o cámara fija,
- detección de personas,
- conteo por mesa,
- zonas de interés,
- estado libre/ocupada,
- inicio y cierre de sesión,
- persistencia de eventos,
- dashboard mínimo,
- ETA baseline simple y explicable.

### Fuera del alcance inicial
- reconocimiento facial,
- audio conversacional continuo,
- identificación de camareros por persona concreta,
- acusación automática de impago,
- multi-cámara real,
- integración completa con POS/TPV,
- analítica avanzada multi-sede.

## Riesgos críticos del proyecto

### Riesgo 1: querer demostrar demasiado en el TFG
Si se intenta abarcar ocupación, ETA, anomalías, impago, audio, multi-cámara y dashboard avanzado al mismo tiempo, el proyecto pierde foco.

### Riesgo 2: no formalizar estados ni eventos
Sin semántica clara, la parte visual produce señales ambiguas y todo lo posterior se vuelve frágil.

### Riesgo 3: mezclar prototipo académico con producto vendible
Para el TFG se puede priorizar velocidad de iteración. Para vender después habrá que revisar licencias, endurecer despliegue y reforzar seguridad, soporte y mantenimiento.

### Riesgo 4: perseguir precisión perfecta demasiado pronto
La meta inicial no es “entender todo lo que pasa en la sala”, sino ayudar a decidir mejor con suficiente fiabilidad.

## Orden de ejecución recomendado

### Paso 1. Cerrar la especificación funcional del MVP
Definir:
- usuario principal,
- problema exacto,
- preguntas que el sistema debe responder,
- entradas y salidas del MVP,
- límites explícitos.

### Paso 2. Formalizar el modelo operacional
Definir:
- estados de mesa,
- eventos admitidos,
- transiciones válidas,
- tiempos relevantes,
- criterios de inicio y fin de sesión.

### Paso 3. Preparar la base técnica real
Crear:
- repositorio ejecutable,
- estructura de carpetas,
- entorno local reproducible,
- configuración mínima,
- convenciones de calidad.

### Paso 4. Implementar el primer pipeline útil
Secuencia mínima:
- frame,
- detección de personas,
- asignación a zona,
- ocupación,
- evento,
- persistencia.

### Paso 5. Crear visibilidad operativa
Añadir:
- vista de estado actual,
- tiempo por sesión,
- historial simple de eventos,
- indicadores básicos de salud del sistema.

### Paso 6. Añadir predicción baseline
Empezar con:
- medias históricas,
- reglas simples,
- intervalos razonables,
- explicación de por qué se predice algo.

### Paso 7. Validar antes de ampliar
No pasar a piloto real ni a anomalías complejas sin:
- pruebas controladas repetibles,
- métricas por módulo,
- errores conocidos documentados,
- criterio de aceptación definido.

## Entregables mínimos de la Fase 0
Antes de programar en serio, conviene dejar cerrados estos entregables:
- especificación funcional del MVP,
- modelo de estados de mesa,
- diccionario de eventos y payloads,
- estructura real de repositorio,
- setup local reproducible,
- plan de pruebas domésticas,
- criterios cuantificados de aceptación para Fase 1.

## Criterios de profesionalidad del proyecto
Cada módulo que se construya debe tener:
- objetivo,
- entradas y salidas,
- dependencias,
- criterio de validación,
- logging mínimo,
- documentación corta de uso,
- limitaciones conocidas.

Cada decisión relevante debe dejar rastro:
- qué se decidió,
- por qué,
- qué alternativa se descartó,
- qué impacto tiene en escalabilidad o comercialización.

## Recomendación sobre escalabilidad y venta futura
El proyecto sí tiene potencial para evolucionar a producto, pero conviene separar mentalmente estas capas:
- **capa académica**: demostrar viabilidad,
- **capa operativa**: lograr un MVP usable,
- **capa empresarial**: licencias, soporte, despliegue repetible, auditoría legal, monitorización y mantenimiento.

La mejor estrategia es construir el MVP de forma que la transición a producto sea posible, pero sin exigir al TFG el coste y la complejidad de un producto ya comercial.

## Siguiente hito recomendado
El siguiente hito lógico no es programar “de todo un poco”, sino producir tres piezas que ordenen el trabajo:
1. una especificación funcional del MVP,
2. un modelo formal de estados y eventos,
3. una estructura real de repositorio para empezar la implementación.

## Estado del proyecto tras esta revisión
Conclusión:
- la idea es potente,
- el enfoque es coherente,
- la documentación de base es buena,
- el proyecto es viable como TFG serio,
- y tiene recorrido real si se mantiene el foco y se ejecuta por capas.

La prioridad ahora no es añadir más ideas, sino reducir ambigüedad y empezar la implementación con una base documental más precisa.
