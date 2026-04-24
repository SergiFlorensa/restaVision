# Tracking y movimiento temporal

## Propósito
Definir cómo usar técnicas clásicas de seguimiento para que RestaurIA pase de detectar presencia puntual a entender:
- trayectoria,
- permanencia,
- entradas y salidas de zona,
- y continuidad de observación en el tiempo.

Este documento cubre:
- puntos característicos,
- flujo óptico,
- seguimiento por densidad,
- plantillas de movimiento,
- y suavizado temporal con estimadores.

## Decisión técnica principal
El tracking no debe ser un requisito duro del MVP más temprano, cuyo núcleo sigue siendo:
- ocupación por mesa,
- sesiones,
- tiempos,
- y eventos básicos.

Sin embargo, sí debe quedar documentado como la siguiente gran capacidad de la capa visual, porque:
- mejora consistencia temporal,
- ayuda con oclusiones,
- y permite pasar de detección estática a comportamiento.

## Problema que resuelve
Sin seguimiento temporal, el sistema observa cada frame casi de forma aislada.

Eso provoca problemas como:
- cambios bruscos de conteo,
- pérdidas temporales de objetos,
- falsas liberaciones por oclusión,
- dificultad para saber si alguien entra, sale o solo se mueve dentro de una mesa.

El tracking intenta mantener continuidad entre observaciones.

## Lugar en la arquitectura
Esta capa pertenece a `services/vision/` y actúa después de:
- detección o segmentación inicial,
- y antes de convertir observaciones en eventos de dominio.

Flujo conceptual:

```text
frame
  -> observaciones visuales
  -> asociación temporal
  -> tracks o trayectorias
  -> señales temporales
  -> eventos de negocio
```

## 1. Selección de características

### Qué aporta
La selección de esquinas o puntos buenos para rastrear permite seguir señales visuales relativamente estables entre frames.

### Valor para RestaurIA
Puede ser útil para:
- movimiento fino dentro de una ROI,
- seguimiento de puntos distintivos de una persona o grupo,
- y experimentos de inclinación, desplazamiento o levantarse de una mesa.

### Decisión
No debe ser el punto de entrada del MVP, pero sí una técnica útil para:
- laboratorio,
- análisis fino,
- o tracking ligero en escenarios controlados.

## 2. Flujo óptico Lucas-Kanade

### Qué aporta
Permite seguir puntos seleccionados entre frames sucesivos.

### Valor práctico
Es útil cuando:
- el movimiento entre frames es moderado,
- hay textura suficiente,
- y se busca seguimiento de bajo coste.

### Aplicación en RestaurIA
Puede servir para:
- mantener continuidad de movimiento local,
- seguir trayectorias en pasillos o entradas,
- o reforzar que una persona que entra en zona sigue siendo la misma durante unos segundos.

### Decisión
Lucas-Kanade piramidal merece quedar como técnica prioritaria de tracking clásico si en la siguiente fase se necesita continuidad temporal de bajo coste.

## 3. Mean-Shift y CamShift

### Qué aportan
En vez de seguir puntos, siguen una distribución densa asociada a color o probabilidad.

### Valor potencial
Pueden ser útiles cuando:
- hay una masa visual coherente,
- interesa mantener una ventana de seguimiento,
- y el objeto cambia ligeramente de escala o posición.

### Aplicación prudente
En RestaurIA podrían explorarse para:
- seguimiento de masa ocupante en una mesa,
- continuidad de grupo dentro de ROI,
- o permanencia visual sin detector complejo.

### Limitaciones
Son sensibles a:
- cambios de color,
- fondos parecidos,
- iluminación,
- y escenas muy concurridas.

### Decisión
Registrar como técnica de exploración útil, no como baseline obligatorio.

## 4. Plantillas de movimiento

### Qué aportan
Las motion templates resumen actividad reciente y dirección predominante del movimiento.

### Valor para el proyecto
Pueden ser muy útiles para detectar:
- aproximación a una mesa,
- salida de una silla,
- movimiento hacia caja o pasillo,
- o interacción de camarero con una zona.

### Decisión
No forman parte del baseline mínimo, pero sí merecen interés porque pueden generar eventos útiles con menos coste que modelos complejos de acción.

## 5. Filtro de Kalman

### Qué aporta
Introduce un modelo simple de predicción y corrección para suavizar trayectorias y resistir oclusiones temporales.

### Valor para RestaurIA
Es especialmente útil cuando:
- una persona queda tapada momentáneamente,
- hay ruido en la detección,
- o se necesita continuidad sin saltos bruscos.

### Aplicación prudente
No es necesario para saber si una mesa está ocupada en el baseline.
Sí puede ser muy valioso cuando se quiera:
- seguir individuos o centroides,
- mantener identidad temporal,
- o evitar falsas salidas por oclusión breve.

### Decisión
Registrar Kalman como la técnica clásica preferente de suavizado temporal cuando el sistema pase de ocupación por ROI a seguimiento explícito.

## Qué señales temporales puede producir esta capa
- trayectoria de un track,
- velocidad aproximada,
- dirección dominante,
- tiempo dentro de zona,
- entrada o salida de ROI,
- persistencia bajo oclusión,
- y estabilidad temporal de identidad local.

## Casos de uso realistas por fase

### MVP temprano
- no tracking obligatorio,
- solo estabilidad temporal básica por ROI.

### MVP ampliado
- seguimiento local en entradas/salidas,
- suavizado temporal de ocupación,
- y persistencia frente a oclusiones breves.

### Fase intermedia
- asociación persona-zona,
- conteo más estable,
- interacción con camareros,
- y detección de patrones de levantarse o abandonar.

## Estrategia recomendada

### Para arrancar
Empezar con:
- señales por ROI,
- consistencia temporal simple,
- histéresis de estado,
- y evitar “tracking completo” si no es necesario aún.

### Para evolucionar
Añadir después:
- Lucas-Kanade piramidal si hace falta seguir puntos,
- Kalman para suavizar,
- motion templates para dirección de actividad,
- y CamShift solo si demuestra utilidad en un caso concreto.

## Qué no conviene hacer todavía
- intentar tracking multipersona robusto desde el primer hito,
- depender de identidad individual fuerte,
- complicar el MVP con demasiadas técnicas temporales a la vez,
- o construir lógica de negocio apoyada en tracks inestables.

## Relación con eventos de negocio
El tracking es especialmente relevante para futuros eventos como:
- entrada_a_mesa,
- salida_de_mesa,
- persona_sale_de_zona,
- permanencia_en_zona,
- aproximacion_a_mesa,
- y posible_finalizacion.

## Riesgos a vigilar
- pérdida de tracks por oclusión,
- intercambio de identidad entre personas cercanas,
- drift del seguimiento,
- falsa continuidad cuando cambia el objeto seguido,
- y complejidad excesiva para el beneficio real del MVP.

## Recomendaciones de laboratorio
- probar tracking solo en escenas controladas al principio,
- medir cuánto mejora frente a la lógica puramente por ROI,
- documentar fallos de oclusión y cruce,
- y no introducir seguimiento completo sin un caso operativo claro.

## Documento complementario
- `docs/03_datos_y_ml/22_estabilizacion_y_validacion_temporal.md`

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`
- `docs/03_datos_y_ml/13_contornos_y_metricas_geometricas.md`
- `docs/02_arquitectura/01_arquitectura_logica.md`

## Conclusión
El tracking es la transición entre ver “ocupación” y entender “comportamiento en el tiempo”.

En RestaurIA no debe adelantarse al MVP, pero sí prepararse bien porque será la base para:
- conteos estables,
- entradas y salidas fiables,
- reducción de falsos vaciados,
- y eventos operativos más ricos en fases siguientes.
