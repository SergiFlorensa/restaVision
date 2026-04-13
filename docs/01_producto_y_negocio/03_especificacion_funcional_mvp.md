# Especificación funcional del MVP

## Propósito
Definir con precisión qué debe hacer el MVP, para quién lo hace, qué información utiliza y cómo sabremos si realmente aporta valor.

## Usuario principal
El usuario principal del MVP es el **responsable de sala**, **host** o **director de turno** que necesita tomar decisiones rápidas sobre mesas y esperas.

## Problema operativo que resuelve
En momentos de alta ocupación, el responsable de sala necesita responder con rapidez a preguntas como:
- qué mesa puede liberarse antes,
- si una mesa sigue ocupada o ya está terminando,
- cuánto tiempo lleva una sesión activa,
- si el tiempo prometido a un grupo es razonable.

Hoy esas respuestas suelen depender de observación manual, intuición y presión operativa.

## Objetivo funcional del MVP
El MVP debe actuar como un **copiloto visual básico** que observe una mesa o zona controlada y convierta esa observación en información operacional útil y trazable.

## Preguntas que el MVP debe poder responder
- ¿La mesa está libre u ocupada?
- ¿Cuántas personas hay aproximadamente en la mesa?
- ¿Cuándo empezó la sesión actual?
- ¿Cuánto tiempo lleva ocupada la mesa?
- ¿Cuál es la estimación baseline de tiempo restante?
- ¿Qué eventos recientes explican el estado actual?

## Alcance funcional

### Funciones incluidas
- captura de vídeo desde webcam o cámara fija,
- detección de personas en la zona observada,
- conteo básico de personas por mesa o zona,
- determinación de mesa libre/ocupada,
- apertura y cierre de sesión de mesa,
- registro de eventos relevantes,
- persistencia en base de datos,
- consulta de sesiones y eventos,
- visualización básica en dashboard,
- cálculo inicial de ETA con lógica simple.

### Funciones excluidas en el MVP
- reconocimiento facial o identificación individual,
- multi-cámara real,
- inferencia emocional,
- audio conversacional,
- clasificación avanzada de platos u objetos,
- acusación automática de fraude o impago,
- integración cerrada con software comercial externo,
- automatización completa de asignación de mesas.

## Entradas del sistema

### Entrada principal
- vídeo local capturado por una webcam o cámara fija.

### Entradas secundarias opcionales
- configuración de zonas,
- capacidad de mesa,
- anotaciones manuales para validación,
- calendario simple de pruebas.

## Salidas del sistema
- estado actual de la mesa,
- número estimado de personas,
- sesión activa con hora de inicio,
- tiempo transcurrido,
- eventos persistidos,
- ETA baseline,
- historial simple consultable en dashboard o API.

## Historias de usuario prioritarias
- Como responsable de sala, quiero ver si una mesa está libre u ocupada para no depender solo de observación manual.
- Como responsable de sala, quiero saber cuánto tiempo lleva una mesa ocupada para anticipar su posible liberación.
- Como responsable de sala, quiero registrar eventos operativos automáticamente para revisar lo ocurrido después.
- Como responsable de sala, quiero una estimación inicial del tiempo restante para prometer esperas más razonables.
- Como desarrollador del sistema, quiero que todo evento relevante quede persistido para poder medir, depurar y entrenar mejor.

## Requisitos no funcionales del MVP
- **Procesamiento local**: el MVP debe funcionar sin dependencia continua de servicios cloud.
- **Latencia razonable**: la información mostrada debe ser útil en tiempo casi real.
- **Explicabilidad**: el estado y la ETA deben poder justificarse con eventos o reglas visibles.
- **Privacidad por diseño**: sin biometría ni identificación nominal.
- **Trazabilidad**: cada evento importante debe poder reconstruirse.
- **Reproducibilidad**: el entorno de desarrollo debe poder montarse de forma repetible.
- **Modularidad**: la lógica de detección no debe acoplarse a la lógica de negocio.

## Supuestos de partida
- el entorno inicial es una mesa o zona controlada,
- la cámara tiene encuadre estable,
- la iluminación es suficientemente consistente,
- las pruebas iniciales se harán en casa o en entorno controlado,
- la precisión perfecta no es requisito del MVP,
- la utilidad operativa pesa más que la sofisticación visual.

## Restricciones
- no depender de APIs de pago para el MVP,
- minimizar el coste de hardware en la fase inicial,
- evitar dependencias con licencias problemáticas en partes difíciles de sustituir,
- no ampliar alcance si antes no hay una métrica mejorada o una necesidad demostrada.

## Criterios de aceptación del MVP
El MVP se considerará funcional cuando cumpla, al menos, lo siguiente:
- detecta correctamente mesa libre/ocupada en escenarios de prueba definidos,
- crea y cierra sesiones de mesa de forma consistente,
- registra eventos con marca temporal,
- muestra estado actual y tiempo acumulado en una interfaz mínima,
- genera una ETA baseline documentada,
- permite revisar errores típicos y casos límite.

## Métricas iniciales a observar
- precisión de ocupación libre/ocupada,
- estabilidad del conteo,
- latencia entre evento observado y evento registrado,
- tasa de falsos cambios de estado,
- utilidad percibida del dashboard,
- error medio de la ETA baseline.

## Dependencias funcionales del MVP
Para que el MVP exista de forma coherente, deben estar disponibles:
- configuración de cámara,
- definición de zona o mesa observada,
- pipeline de detección,
- modelo de eventos,
- persistencia,
- endpoint o interfaz de consulta.

## Decisiones que este documento deja fijadas
- el núcleo del MVP no es “vigilar el restaurante”, sino apoyar decisiones de sala,
- el primer caso de uso es una mesa o zona controlada,
- el valor inicial está en estados, tiempos y trazabilidad,
- la predicción es baseline y explicable, no avanzada ni opaca,
- el proyecto se construirá para poder escalar, pero sin cargar al MVP con problemas de producto final.

## Relación con las siguientes piezas de documentación
Después de este documento, las dos piezas más importantes son:
1. el modelo formal de estados de mesa,
2. el diccionario de eventos y payloads.

Sin esas dos piezas, la implementación puede avanzar técnicamente, pero no de forma ordenada.
