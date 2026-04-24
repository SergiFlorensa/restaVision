# Calibración de cámara y precisión métrica

## Propósito
Definir cómo RestaurIA debe abordar la calibración de cámara para pasar de una lectura puramente visual basada en píxeles a una lectura geométrica más estable y, cuando sea necesario, con relación al espacio físico real del restaurante.

Este documento cubre:
- distorsión de lente,
- parámetros intrínsecos,
- calibración con patrón,
- undistortion eficiente,
- y preparación para mediciones con sentido físico.

## Decisión técnica principal
La calibración de cámara no debe bloquear el MVP doméstico más simple, pero sí debe formar parte explícita de la arquitectura desde ahora.

Regla de proyecto:
- **laboratorio doméstico**: puede arrancar con configuración geométrica sin calibración intrínseca completa si la cámara es estable y la precisión requerida es baja,
- **piloto real y despliegue serio**: debe contemplar calibración de cámara y corrección de distorsión como capacidad técnica formal.

## Problema que resuelve esta capa
Sin calibración, el sistema trabaja sobre una imagen deformada por:
- distorsión radial,
- distorsión tangencial,
- y proyección no lineal del lente.

Esto puede causar:
- que una mesa parezca invadir otra,
- que un punto cerca del borde quede desplazado,
- que las zonas se deformen,
- o que la pertenencia a una ROI falle en cámaras baratas o angulares.

## Distorsión de lente

### Distorsión radial
Problema:
- los puntos se curvan hacia dentro o hacia fuera,
- especialmente cerca de los bordes de la imagen.

Impacto en RestaurIA:
- zonas mal alineadas,
- errores en mesas laterales,
- y falsa lectura de cercanía o salida de zona.

### Distorsión tangencial
Problema:
- el sistema óptico no está perfectamente alineado,
- y los puntos se desplazan de forma asimétrica.

Impacto:
- deformación menos intuitiva,
- pero suficiente para empeorar calibración y exactitud espacial.

## Matriz intrínseca

### Qué representa
La matriz intrínseca resume la geometría interna de la cámara:
- focales efectivas,
- centro óptico,
- escala en el plano de imagen.

### Por qué importa
Sin esta matriz:
- el sistema solo conoce posiciones en píxeles.

Con ella:
- puede corregir proyección,
- preparar homografías más fiables,
- y acercarse a relaciones espaciales más reales.

## Calibración con tablero

### Estrategia recomendada
Usar un patrón controlado, preferiblemente tablero de ajedrez, porque:
- las esquinas internas son detectables con precisión,
- se refinan bien a subpíxel,
- y OpenCV ofrece soporte maduro para esta tarea.

### Qué hace falta
- varias capturas del patrón,
- orientaciones distintas,
- distintas posiciones en el frame,
- y medidas físicas conocidas del cuadrado.

### Regla práctica
La calibración debe:
- cubrir buena parte del campo visual,
- incluir esquinas y centro,
- y no limitarse a una única orientación del tablero.

## Refinamiento subpíxel

### Valor práctico
Refinar esquinas antes de resolver la calibración mejora la calidad de:
- la matriz intrínseca,
- la estimación de distorsión,
- y la estabilidad del undistortion posterior.

### Decisión
Si se implementa calibración, el refinamiento subpíxel debe considerarse parte normal del flujo y no un extra opcional.

## Resultado esperado de la calibración
Por cámara, el sistema debería poder obtener y persistir:
- matriz intrínseca,
- coeficientes de distorsión,
- error de reproyección o medida equivalente,
- metadatos del patrón,
- y fecha o versión de calibración.

## Persistencia de calibración

### Regla de diseño
La calibración no debe repetirse cada vez que arranca el sistema.

Debe:
- ejecutarse una vez por cámara y montaje,
- guardarse en archivo persistente,
- cargarse al iniciar,
- y ser invalidable si cambia el montaje físico.

### Formato razonable
Para el proyecto:
- YAML o JSON estructurado,
- o formato compatible con OpenCV si resulta más práctico.

## Undistortion eficiente en tiempo real

### Problema
Corregir distorsión de forma ingenua en cada frame puede penalizar latencia.

### Estrategia recomendada
Precalcular mapas de remapeo una sola vez al inicio y aplicarlos en tiempo de ejecución.

### Valor para RestaurIA
Esto permite:
- mantener corrección estable,
- no recalcular geometría en cada frame,
- y usar la calibración en producción sin coste desproporcionado.

## Relación con rectificación y homografía
La calibración intrínseca y la homografía no son lo mismo.

### Calibración intrínseca
Corrige la cámara como sensor/lente.

### Homografía
Rectifica la relación entre un plano del mundo y la imagen.

### Combinación recomendada
Cuando el caso lo requiera:
1. corregir distorsión,
2. aplicar rectificación geométrica si hace falta,
3. procesar zonas en un espacio más fiable.

## Qué aporta la precisión métrica
En el MVP temprano no necesitamos medir centímetros exactos para saber si una mesa está ocupada.

Pero sí es valioso dejar abierta la puerta a:
- distancias reales en el suelo,
- anchura de paso,
- tamaño relativo de zonas,
- mejor modelado espacial,
- y análisis más serio en piloto real.

## Cuándo merece la pena calibrar

### Sí conviene
- cámara fija definitiva,
- piloto real,
- lente gran angular,
- errores espaciales cerca de bordes,
- o necesidad de homografía fiable.

### Puede esperar
- laboratorio doméstico sencillo,
- una sola mesa bien centrada,
- precisión espacial no crítica,
- y pruebas cuyo objetivo sea validar la cadena funcional.

## Riesgos a vigilar
- calibración mal hecha que empeora la imagen,
- patrón mal medido,
- número insuficiente de vistas,
- usar calibración vieja tras mover la cámara,
- y mezclar parámetros de cámaras distintas.

## Recomendaciones de laboratorio
- guardar dataset de calibración por cámara,
- registrar error de reproyección,
- comparar visualmente frame original vs. corregido,
- validar que zonas laterales mejoran,
- y no aceptar calibración “porque sí” sin mejora observable.

## Cómo encaja en la herramienta de setup
La herramienta de calibración o setup debería poder:
- lanzar captura de patrón,
- detectar esquinas,
- mostrar validación visual,
- guardar la calibración,
- y asociarla a una `camera_id`.

## Qué entra en el MVP
- soporte documental y estructural para calibración,
- persistencia por cámara,
- capacidad opcional de undistortion,
- y relación clara con rectificación posterior.

## Qué se deja para después
- mediciones físicas avanzadas,
- reconstrucción 3D compleja,
- validaciones geométricas sofisticadas,
- y proyecciones más allá del plano útil del restaurante.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/04_software_y_devops/08_highgui_herramienta_de_calibracion.md`
- `docs/02_arquitectura/02_arquitectura_fisica_y_despliegue.md`

## Conclusión
La calibración de cámara es la capacidad que convierte a RestaurIA de un sistema visual aproximado en un sistema con fundamento geométrico serio.

No debe frenar el arranque del MVP doméstico, pero sí debe quedar integrada en la arquitectura desde ya para que el paso a piloto real no obligue a rehacer la base técnica.
