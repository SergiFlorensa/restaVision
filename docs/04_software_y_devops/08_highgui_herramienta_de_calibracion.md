# HighGUI y herramienta de calibración

## Propósito
Definir cómo utilizar HighGUI de OpenCV dentro de RestaurIA como herramienta de:
- laboratorio,
- calibración,
- ajuste visual,
- depuración,
- y grabación de evidencia.

Este documento deja fijada una decisión importante:
- **HighGUI sí para herramientas internas de visión**,
- **HighGUI no como dashboard operativo final del producto**.

## Decisión técnica principal
La API de ventanas de OpenCV es útil para prototipado y utilidades técnicas, pero no debe considerarse la interfaz final del sistema.

Por tanto:
- el **dashboard operativo** de RestaurIA vivirá fuera de HighGUI,
- mientras que la **configuración de cámaras, ROIs y depuración visual** sí puede apoyarse en `cv2.imshow`, callbacks de ratón y trackbars.

## Qué papel cumple HighGUI en RestaurIA
HighGUI encaja especialmente bien en estas tareas:
- mostrar vídeo anotado,
- dibujar zonas y mesas,
- ajustar umbrales en tiempo real,
- inspeccionar máscaras o transformaciones,
- alternar vistas de depuración,
- y grabar clips cuando aparece un evento relevante.

## Casos de uso recomendados

### 1. Modo Setup
Objetivo:
- permitir que una persona configure la geometría inicial del local.

Capacidades:
- mostrar frame de referencia,
- marcar esquinas o polígonos con el ratón,
- visualizar IDs de zona,
- guardar la configuración en archivo.

Extensión recomendable:
- soportar modo de captura de patrón de calibración por cámara.

### 2. Modo Debug
Objetivo:
- entender qué está haciendo el pipeline.

Capacidades:
- ver vídeo original,
- ver ROI,
- ver máscara intermedia,
- ver overlays de estado,
- y alternar capas de explicación.

### 3. Modo Tuning
Objetivo:
- ajustar parámetros del pipeline durante pruebas.

Capacidades:
- sliders de umbral,
- switches binarios,
- comparación visual inmediata,
- y captura rápida de configuración válida.

### 4. Modo Evidencia
Objetivo:
- guardar clips o imágenes cuando cambia el estado de una mesa o aparece una anomalía.

Capacidades:
- escribir vídeo anotado,
- guardar snapshots,
- y asociar evidencia a un evento técnico.

## Sistema de ventanas

### Qué mostrar
Durante laboratorio o configuración, las ventanas útiles pueden ser:
- `frame_original`
- `frame_anotado`
- `mask_movimiento`
- `roi_debug`
- `configuracion_zonas`

### Principio de uso
Las ventanas deben existir para facilitar decisiones técnicas, no para replicar un dashboard de producción.

Eso significa:
- pocas ventanas,
- nombres claros,
- estado visible,
- y cierre limpio.

## Control del refresco y del bucle
En OpenCV, el refresco visual depende del procesamiento del bucle y de la llamada correspondiente al teclado/event loop.

Aplicación práctica:
- la herramienta debe mantener un bucle claro,
- evitar bloqueos innecesarios,
- y permitir salir o pausar de forma explícita.

## Interacción con ratón

### Uso principal
Los callbacks de ratón son especialmente útiles para:
- definir rectángulos de mesa,
- dibujar polígonos,
- mover puntos de anclaje,
- seleccionar una zona para inspección,
- y confirmar o corregir geometría.

### Recomendación de diseño
La herramienta de setup debe soportar al menos:
- clic para añadir punto,
- arrastre para rectángulo,
- borrado o reinicio de selección,
- y confirmación final antes de guardar.

Para el MVP temprano, debe ser especialmente fácil:
- dibujar un rectángulo de mesa,
- previsualizar la ROI resultante,
- y guardar varias mesas sin reconfigurar toda la escena.

## Trackbars y switches

### Para qué sirven
Los controles deslizantes son apropiados para:
- umbrales de movimiento,
- sensibilidad de diferencia,
- tamaño mínimo de área,
- parámetros visuales de máscara,
- activación o desactivación de capas de debug.

### Regla de uso
Las trackbars son válidas para experimentación.
No deben convertirse en el mecanismo principal de operación de producción.

## Configuración geométrica del local

### Qué debe permitir la herramienta
- cargar configuración previa,
- superponerla sobre el frame,
- editar zonas existentes,
- añadir nuevas zonas,
- y exportar resultado.

### Formato de salida
La herramienta debe guardar la configuración en `YAML` o `JSON`.

Datos mínimos:
- `camera_id`
- `zone_id`
- `zone_type`
- `label`
- `geometry`
- `roi_bbox`
- `capacity`
- `active`

## Overlays y feedback visual

### Capas útiles
El vídeo anotado debería poder mostrar:
- contorno de mesa o zona,
- estado actual,
- confianza,
- tiempo de sesión,
- conteo de personas,
- ETA si existe,
- y color según estado.

### Principio
El overlay debe explicar, no decorar.

Si el sistema dibuja algo, debe aportar:
- trazabilidad,
- comprensión,
- o capacidad de depuración.

### Dibujo de mesas rectangulares
Para el MVP temprano, la representación visual más simple de una mesa será un rectángulo.

Lógica conceptual:
- la geometría se define por `x`, `y`, `width`, `height`,
- y se dibuja a partir de dos esquinas opuestas:
- superior izquierda: `(x, y)`
- inferior derecha: `(x + width, y + height)`

Adaptación moderna recomendada:
- usar `cv2.rectangle(...)`,
- no `cvRectangle(...)` de la API C clásica.

Ejemplo conceptual:

```python
cv2.rectangle(
    frame,
    (x, y),
    (x + width, y + height),
    color_bgr,
    thickness,
)
```

### Colores por estado
La representación visual debe ayudar a interpretar el estado de la mesa de un vistazo.

Ejemplo razonable:
- verde para `libre`,
- rojo para `ocupada`,
- amarillo para `finalizando`,
- azul o cian para `limpieza`,
- gris para `inactiva` o sin señal.

### Contorno vs relleno
La herramienta debería soportar dos modos:
- contorno: útil para no tapar la escena,
- relleno translúcido: útil para depuración de ocupación o calor visual.

Regla práctica:
- en laboratorio, el contorno suele bastar;
- el relleno debe usarse con transparencia o de forma limitada para no ocultar información importante del frame.

## Escritura de vídeo y evidencia

### Cuándo grabar
La grabación automática puede ser útil cuando:
- una mesa cambia de estado,
- aparece un evento anómalo,
- falla una predicción,
- o se quiere crear dataset de validación.

### Qué conviene guardar
- clip corto antes y después del evento,
- frame anotado,
- metadatos del evento,
- y referencia temporal para revisión posterior.

### Regla operativa
No guardar vídeo indiscriminadamente.
La captura persistente debe estar controlada por:
- finalidad,
- espacio en disco,
- y política de privacidad.

## Arquitectura recomendada

### `services/vision/`
Responsable de:
- render de overlays,
- callbacks de configuración,
- controles de laboratorio,
- escritura de clips técnicos.

### `apps/worker/`
Responsable de:
- activar o desactivar modos técnicos,
- ejecutar el pipeline,
- y decidir cuándo se produce evidencia.

### Dashboard final
Debe considerarse otro producto dentro del repositorio, separado del laboratorio visual.

## Límites de HighGUI

### Lo que sí hace bien
- prototipado rápido,
- depuración visual,
- ajuste de parámetros,
- configuración manual,
- y validación técnica temprana.

### Lo que no debe resolver
- UX final de producción,
- dashboards multiusuario,
- gestión avanzada de estado de aplicación,
- interacción compleja de negocio,
- ni despliegue operativo estable de cara al usuario final.

## Relación con el roadmap
Este documento alimenta directamente:
- Fase 0 y Fase 1,
- configuración de cámara,
- definición inicial de zonas,
- depuración del primer pipeline,
- y creación temprana de dataset y evidencia.

## Conclusión
El valor de HighGUI en RestaurIA está en permitir que el sistema se vea, se ajuste y se entienda durante el desarrollo.

Su papel correcto es ser una herramienta técnica de:
- calibración,
- laboratorio,
- depuración,
- y evidencia.

Eso acelera el MVP sin hipotecar la calidad del dashboard final, que deberá diseñarse con criterios de producto y operación más sólidos.
