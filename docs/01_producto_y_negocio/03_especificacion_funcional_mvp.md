# Especificacion funcional del MVP

## Proposito
Definir con precision que debe hacer el MVP, para quien lo hace, que informacion utiliza y como sabremos si realmente aporta valor.

## Usuario principal
El usuario principal del MVP es el **responsable de sala**, **host** o **director de turno** que necesita tomar decisiones rapidas sobre mesas, esperas y prioridades durante el servicio.

## Problema operativo que resuelve
En momentos de alta ocupacion, el responsable de sala necesita responder con rapidez:
- que hago ahora,
- que mesa puedo preparar,
- que espera puedo prometer,
- que mesa se esta bloqueando,
- que grupo conviene sentar primero,
- que alerta merece atencion inmediata.

Hoy esas respuestas dependen de observacion manual, intuicion y presion operativa.

## Objetivo funcional del MVP
El MVP debe actuar como un **copiloto operativo basico**. Debe convertir estados, eventos y tiempos en recomendaciones accionables, no solo en visualizaciones tecnicas.

## Preguntas que el MVP debe poder responder
- Cual es la accion principal ahora?
- Cuales son las tres acciones siguientes?
- Que mesa compatible puede liberarse antes?
- Que espera realista se puede prometer a un grupo en cola?
- Que mesas estan libres, ocupadas, finalizando, pendientes de limpieza o requieren atencion?
- Que eventos recientes explican una recomendacion?

## Alcance funcional

### Funciones incluidas
- captura de video desde webcam o camara fija,
- configuracion de mesas, zonas y capacidades,
- deteccion o entrada manual de ocupacion,
- cola manual asistida,
- apertura y cierre de sesiones de mesa,
- registro de eventos relevantes,
- persistencia en base de datos,
- ETA baseline con logica simple,
- calculo inicial de presion operativa,
- generacion de recomendaciones `Next Best Action`,
- Promise Engine inicial para esperas,
- dashboard de operacion con accion principal y top 3 acciones.

### Funciones excluidas en el MVP
- reconocimiento facial o identificacion individual,
- multi-camara real,
- inferencia emocional,
- audio conversacional,
- clasificacion avanzada de platos u objetos como dependencia critica,
- acusacion automatica de fraude o impago,
- integracion cerrada con software comercial externo,
- automatizacion completa de asignacion de mesas sin supervision humana.

## Entradas del sistema

### Entrada principal
- estado de mesas y sesiones,
- cola manual asistida,
- configuracion de zonas y capacidades,
- eventos operativos.

### Entradas secundarias
- video local capturado por webcam o camara fija,
- anotaciones manuales para validacion,
- calendario simple de pruebas,
- feedback del encargado sobre recomendaciones.

## Salidas del sistema
- accion principal recomendada,
- top 3 acciones,
- prioridad P1/P2/P3,
- ETA o rango de espera,
- promesa recomendada al cliente,
- estado actual de mesas,
- eventos persistidos,
- explicacion breve de cada recomendacion,
- historial consultable por API o dashboard.

## Historias de usuario prioritarias
- Como responsable de sala, quiero saber que accion ejecutar ahora para no interpretar un dashboard en plena presion.
- Como responsable de sala, quiero una espera realista para comunicar al grupo de entrada.
- Como responsable de sala, quiero saber que mesa preparar primero para reducir cola.
- Como responsable de sala, quiero detectar mesas desatendidas o bloqueadas antes de que generen mal servicio.
- Como desarrollador del sistema, quiero que cada recomendacion quede explicada y persistida para medir si funciono.

## Requisitos no funcionales del MVP
- **Procesamiento local**: el MVP debe funcionar sin dependencia continua de servicios cloud.
- **Latencia razonable**: la informacion mostrada debe ser util en tiempo casi real.
- **Explicabilidad**: el estado, la ETA y la recomendacion deben justificarse con eventos o reglas visibles.
- **Privacidad por diseno**: sin biometria ni identificacion nominal.
- **Trazabilidad**: cada evento y decision importante debe poder reconstruirse.
- **Reproducibilidad**: el entorno de desarrollo debe poder montarse de forma repetible.
- **Modularidad**: la logica de deteccion no debe acoplarse a la logica de negocio.

## Supuestos de partida
- el entorno inicial es una mesa o zona controlada,
- la camara tiene encuadre estable si se usa vision,
- la cola puede introducirse manualmente al principio,
- la precision perfecta no es requisito del MVP,
- la utilidad operativa pesa mas que la sofisticacion visual.

## Restricciones
- no depender de APIs de pago para el MVP,
- minimizar el coste de hardware en la fase inicial,
- evitar dependencias con licencias problematicas en partes dificiles de sustituir,
- no ampliar alcance si antes no hay una metrica mejorada o una necesidad demostrada.

## Criterios de aceptacion del MVP
El MVP se considerara funcional cuando cumpla, al menos, lo siguiente:
- persiste mesas, sesiones, eventos y recomendaciones,
- muestra accion principal y top 3 acciones,
- permite registrar grupos en cola,
- genera una promesa de espera baseline,
- calcula ETA baseline documentada,
- explica por que recomienda una accion,
- permite registrar feedback de una recomendacion,
- mantiene un modo de operacion con ruido visual minimo.

## Metricas iniciales a observar
- error medio de ETA,
- promesas de espera incumplidas,
- acciones recomendadas,
- acciones aceptadas,
- acciones marcadas como utiles,
- tiempo hasta primera atencion,
- tiempo medio de cola,
- mesas bloqueadas detectadas,
- falsos positivos de alertas P1/P2,
- utilidad percibida de la pantalla operativa.

## Dependencias funcionales del MVP
Para que el MVP exista de forma coherente, deben estar disponibles:
- configuracion de camara,
- definicion de zona o mesa observada,
- modelo de eventos,
- persistencia,
- cola manual asistida,
- motor de decision,
- endpoint o interfaz de consulta.

## Decisiones que este documento deja fijadas
- el nucleo del MVP no es vigilar el restaurante, sino apoyar decisiones de sala,
- la vision artificial es una fuente de evidencia, no el producto completo,
- el primer caso de uso es una mesa o zona controlada con cola manual,
- el valor inicial esta en accion, espera prometible, trazabilidad y explicabilidad,
- la prediccion es baseline y explicable, no avanzada ni opaca,
- el proyecto se construira para poder escalar, pero sin cargar al MVP con problemas de producto final.

## Relacion con las siguientes piezas de documentacion
Despues de este documento, las piezas mas importantes son:
1. configuracion operativa del copiloto,
2. modelo formal de estados de mesa,
3. diccionario de eventos y payloads,
4. esquema de datos,
5. motor de decision.
