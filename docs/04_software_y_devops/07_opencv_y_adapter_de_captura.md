# OpenCV y adaptador de captura

## Propósito
Traducir los conceptos fundamentales de captura y procesamiento de vídeo de OpenCV a una arquitectura moderna y mantenible para RestaurIA.

Este documento toma como base los principios clásicos del capítulo de introducción a OpenCV, pero los adapta al stack real del proyecto:
- Python,
- `cv2`,
- arquitectura modular,
- y separación entre captura, procesamiento y lógica de negocio.

## Decisión técnica principal
Aunque el capítulo original se apoya en la API clásica en C (`CvCapture`, `cvQueryFrame`, `cvWaitKey`, etc.), en RestaurIA se trabajará con la API moderna de OpenCV para Python.

Equivalencias conceptuales:
- `CvCapture` -> `cv2.VideoCapture`
- `cvQueryFrame` -> `capture.read()`
- `cvWaitKey` -> control de render, teclado y ritmo de bucle
- `cvReleaseCapture` -> `capture.release()`
- `cvSmooth` -> `cv2.GaussianBlur` u otros filtros
- `cvPyrDown` -> `cv2.pyrDown` o `cv2.resize`
- `cvCanny` -> `cv2.Canny`

## Rol de OpenCV en RestaurIA
OpenCV cubrirá, sobre todo, estas funciones:
- captura desde cámara o archivo,
- preprocesado de frames,
- depuración visual,
- prototipado rápido,
- y utilidades de bajo nivel para el pipeline inicial.

No será necesariamente el motor completo de detección final, pero sí la base del adaptador de entrada y del procesamiento temprano.

## Diseño del adaptador de captura

### Objetivo
El adaptador de captura debe desacoplar la fuente de vídeo del resto del sistema.

Esto permitirá usar el mismo flujo para:
- pruebas con vídeo grabado,
- laboratorio doméstico,
- cámara en tiempo real,
- y futuras fuentes IP o RTSP.

### Responsabilidades del adaptador
- abrir la fuente de vídeo,
- validar disponibilidad,
- leer frames de forma secuencial,
- normalizar metadatos básicos,
- liberar recursos correctamente,
- y exponer una interfaz estable al resto del sistema.

### Interfaz conceptual esperada
El sistema debería poder hacer algo como:

```python
capture = CaptureAdapter(source=config.source)

frame_packet = capture.read()

if frame_packet is None:
    ...
```

Donde `frame_packet` incluya al menos:
- `frame`,
- `timestamp`,
- `frame_index`,
- `source_id`,
- `width`,
- `height`.

## Fuentes de captura que deben soportarse

### 1. Archivo de vídeo
Uso principal:
- pruebas reproducibles,
- depuración,
- comparación de algoritmos,
- demos controladas.

Ventaja:
- permite repetir exactamente la misma escena.

### 2. Cámara local
Uso principal:
- laboratorio doméstico,
- MVP en tiempo real,
- validación inicial.

### 3. Fuente futura IP/RTSP
No es requisito del MVP inicial, pero conviene que el adaptador no cierre esa puerta de diseño.

## Bucle base de procesamiento
El flujo mínimo esperado es:

```text
fuente de vídeo
  -> lectura de frame
  -> validación
  -> preprocesado
  -> inferencia o análisis
  -> generación de observaciones
  -> eventos
  -> persistencia / visualización
```

## Control temporal

### Qué queremos controlar
- ritmo de lectura,
- frecuencia efectiva de procesamiento,
- latencia,
- muestreo,
- y comportamiento al final del stream.

### Implicación práctica
En RestaurIA no conviene acoplar la lógica de negocio a la velocidad nativa de la cámara.

El adaptador debe permitir:
- leer todos los frames si hace falta,
- muestrear cada `n` frames,
- limitar FPS efectivo,
- o desacoplar captura de procesamiento en fases posteriores.

## Preprocesado inicial recomendado

### Suavizado
Sirve para:
- reducir ruido,
- estabilizar señales,
- mejorar etapas posteriores.

Opciones razonables:
- `cv2.GaussianBlur`
- `cv2.medianBlur`

### Reducción de escala
Útil cuando:
- el hardware es modesto,
- se necesita latencia menor,
- o se está prototipando lógica antes que precisión máxima.

Opciones razonables:
- `cv2.resize`
- `cv2.pyrDown`

### Detección de bordes
No será necesariamente el motor central del MVP, pero puede ser útil para:
- análisis exploratorio,
- segmentación temprana,
- depuración visual,
- experimentos con ocupación y contorno de zona.

## Herramientas de prototipado y ajuste

### Trackbars
Las barras deslizantes son valiosas en fase de laboratorio para:
- ajustar umbrales,
- visualizar sensibilidad,
- probar filtros,
- y depurar rápidamente sin editar código en cada prueba.

### Uso recomendado
Las trackbars deben considerarse una herramienta de experimentación local, no una solución final de producto.

Es decir:
- sí en prototipo,
- no como mecanismo central de operación del sistema en producción.

Referencia complementaria:
- `docs/04_software_y_devops/08_highgui_herramienta_de_calibracion.md`

## Gestión de memoria y estabilidad

### Regla principal
El sistema solo debe liberar explícitamente los recursos que haya creado o posea directamente.

### Riesgos a evitar
- duplicar frames innecesariamente,
- mantener buffers sin límite,
- olvidar `release()` de cámara,
- mezclar responsabilidades de captura y procesamiento,
- y conservar referencias a frames mutables más tiempo del necesario.

### Principio de diseño
Cada etapa del pipeline debe dejar claro:
- qué recibe,
- qué modifica,
- qué copia,
- y qué devuelve.

## Separación de responsabilidades en el código

### Capa `services/vision/`
Responsable de:
- captura,
- preprocesado,
- utilidades visuales,
- y conversión de frame a observaciones.

### Capa `services/events/`
Responsable de:
- traducir observaciones a eventos operativos.

### Capa `apps/worker/`
Responsable de:
- ejecutar el bucle de procesamiento,
- coordinar captura, análisis y persistencia.

## Recomendaciones para el MVP

### Lo que sí conviene hacer
- soportar vídeo y webcam desde el inicio,
- guardar metadatos del frame,
- permitir depuración visual básica,
- registrar FPS y latencia,
- y crear un pipeline simple y trazable.

### Lo que no conviene hacer todavía
- optimización prematura compleja,
- múltiples cámaras simultáneas,
- buffering sofisticado sin necesidad,
- threading avanzado sin métricas previas,
- y mezclar UI final con prototipado técnico.

## Salidas mínimas esperadas del subsistema de captura
El subsistema de captura debe poder entregar:
- frame actual,
- estado de la fuente,
- error si la fuente falla,
- metadatos temporales,
- y una forma simple de cerrar la sesión de captura sin fugas de recursos.

## Relación con el roadmap del proyecto
Este documento alimenta directamente:
- Fase 1: laboratorio doméstico con una mesa,
- Épica de captura,
- Épica de detección,
- y el primer pipeline `frame -> observación -> evento`.

Documento específico complementario:
- `docs/04_software_y_devops/09_video_to_observation_adapter.md`

## Conclusión
El valor real del capítulo de OpenCV para RestaurIA no está en copiar la API antigua, sino en fijar una disciplina de ingeniería:
- separar captura y procesamiento,
- controlar bien recursos y tiempo,
- prototipar con herramientas simples,
- y construir un adaptador de vídeo reutilizable para pruebas y operación real.
