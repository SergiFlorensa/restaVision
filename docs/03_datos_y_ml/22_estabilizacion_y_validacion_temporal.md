# Estabilización y validación temporal

## Propósito
Definir cómo usar información temporal para hacer a RestaurIA más robusto frente a:
- microvibraciones de cámara,
- oclusiones breves,
- falsos positivos de sustracción de fondo,
- y variaciones temporales de un stream inalámbrico.

Este documento cubre:
- estabilización básica por movimiento,
- tracking por color como apoyo,
- validación cruzada entre fondo y trayectoria,
- y uso correcto del tiempo real del stream.

## Decisión técnica principal
Estas capacidades tienen valor real, pero no deben bloquear el MVP más simple.

Regla:
- si la cámara es estable y el laboratorio está controlado, no complicar el pipeline;
- si la cámara inalámbrica introduce jitter, pérdida de referencia o frames irregulares, entonces estas técnicas sí pasan a ser relevantes.

## 1. Estabilización por movimiento

### Qué problema resuelve
Si la cámara se desplaza ligeramente:
- las ROIs dejan de coincidir exactamente,
- la sustracción de fondo se degrada,
- y puede parecer que toda la escena cambia aunque la mesa siga igual.

### Idea útil
Seguir puntos de interés entre frames y estimar el desplazamiento global de la imagen para compensarlo.

### Valor para RestaurIA
Esto puede ayudar a:
- mantener la geometría de mesas alineada,
- reducir falsos cambios de ocupación,
- y estabilizar streams inalámbricos o montajes físicos menos firmes.

### Decisión
La estabilización debe considerarse:
- capacidad opcional por cámara,
- no paso universal fijo del sistema.

## 2. Mean-Shift y CamShift como apoyo temporal

### Qué aportan
Permiten seguir una distribución visual densa entre frames.

### Uso razonable en el proyecto
Pueden ser útiles para:
- seguir una masa ocupante local,
- mantener continuidad de una región,
- o analizar presencia de personal con una señal controlada como uniforme.

### Restricción importante
No deben convertirse en base primaria de identidad de personas ni en una lógica frágil apoyada en color humano sensible.

### Decisión
Mantenerlos como herramientas de:
- exploración,
- tracking local de bajo coste,
- y apoyo puntual cuando una señal cromática estable exista de verdad.

## 3. Validación cruzada entre fondo y movimiento

### Idea central
Una detección de ocupación no debería depender siempre de una única fuente.

Ejemplo:
- si el modelo de fondo detecta un cambio fuerte,
- pero no existe ninguna trayectoria de entrada ni actividad coherente,
- esa observación puede tratarse con más cautela.

### Valor para RestaurIA
Este principio es muy potente porque reduce falsos positivos causados por:
- sombras,
- cambios de exposición,
- jitter,
- o artefactos del stream.

### Traducción operativa
El sistema puede introducir una regla de consistencia, por ejemplo:
- cambio de fondo sin movimiento ni historia reciente de entrada = observación sospechosa,
- cambio de fondo + trayectoria o actividad coherente = observación más confiable.

### Decisión
Esta validación cruzada sí merece quedar como patrón de diseño importante para el motor de observación.

## 4. Oclusiones y continuidad temporal

### Problema
En sala, una persona puede quedar tapada por:
- un camarero,
- otra persona,
- o un objeto transitorio.

Sin continuidad temporal, el sistema puede interpretar:
- falsa salida,
- falsa mesa liberada,
- o reinicio erróneo de sesión.

### Solución conceptual
Usar suavizado temporal y predicción para asumir que:
- una desaparición breve no implica cambio real instantáneo de estado.

### Decisión
No hace falta introducir un filtro completo en el MVP temprano,
pero sí dejar la regla de negocio clara:
- las desapariciones breves no deben volcar el estado sin histéresis ni confirmación temporal.

## 5. Filtro de Kalman como siguiente escalón

### Qué aporta
Predicción y corrección bajo ruido y oclusión parcial.

### Cuándo tiene sentido
- si existe tracking explícito,
- si las oclusiones dañan mucho la estabilidad,
- o si la continuidad de tracks ya es un requisito.

### Decisión
Kalman debe quedar documentado como técnica preferente cuando la continuidad temporal deje de ser solo una heurística y pase a ser un módulo explícito de tracking.

## 6. Timestamps y tiempo real del stream

### Qué problema resuelve
En streams inalámbricos:
- los frames pueden llegar con jitter,
- el reloj local no siempre representa bien el momento real del frame,
- y asumir un FPS fijo puede introducir error temporal.

### Regla de proyecto
Siempre que sea posible, las observaciones deben conservar:
- timestamp del frame o del stream,
- índice de frame,
- y referencia temporal coherente por fuente.

### Valor para RestaurIA
Esto es importante para:
- duración de sesiones,
- cálculo de ETA,
- ventanas de movimiento,
- y consistencia temporal de eventos.

## 7. FPS real vs. FPS nominal

### Riesgo
Un stream inalámbrico puede no entregar realmente el FPS nominal anunciado.

### Consecuencia
Si el sistema asume 30 FPS y en realidad recibe menos o con jitter:
- los cálculos de tiempo,
- movimiento,
- velocidad,
- y ETA
pueden distorsionarse.

### Decisión
El sistema debe desacoplar:
- tiempo de captura,
- tiempo de observación,
- y tiempo lógico de negocio,
usando timestamps reales cuando estén disponibles.

## Estrategia recomendada por fases

### MVP temprano
- histéresis temporal básica,
- validación cruzada simple entre señales,
- timestamps por frame,
- sin estabilización compleja salvo necesidad.

### MVP ampliado
- estabilización opcional por cámara,
- tracking local ligero,
- y reglas temporales más ricas.

### Fase intermedia
- Kalman,
- mayor continuidad de tracks,
- y tratamiento explícito de oclusiones.

## Qué entra realmente en el proyecto

### Sí entra como patrón importante
- validación cruzada entre señales de fondo y movimiento,
- timestamps por frame,
- y tratamiento prudente de desapariciones breves.

### Queda como capacidad opcional
- estabilización por flujo óptico,
- CamShift/Mean-Shift,
- y Kalman.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/15_tracking_y_movimiento_temporal.md`
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`
- `docs/04_software_y_devops/09_video_to_observation_adapter.md`
- `docs/04_software_y_devops/10_estrategia_de_latencia_y_rendimiento.md`

## Conclusión
La estabilidad temporal de RestaurIA no debe depender de que el vídeo llegue perfecto.

La combinación correcta es:
- señales locales,
- validación cruzada,
- tiempo bien registrado,
- y técnicas de seguimiento o estabilización solo cuando el entorno real lo exija.

Eso permite que el sistema siga siendo explicable y robusto sin introducir complejidad prematura.
