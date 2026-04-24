# Decisión Python vs C++ para visión

## Propósito
Dejar fijada la decisión técnica sobre en qué lenguaje debe implementarse la capa de visión de RestaurIA, especialmente a la luz de la transición histórica de OpenCV desde la API C a la interfaz moderna de C++.

Este documento responde a una pregunta concreta:
- ¿debemos construir RestaurIA en Python o en C++?

## Conclusión ejecutiva
La decisión correcta para el estado actual del proyecto es:
- **Python como lenguaje principal del MVP y del sistema base**
- **C++ solo como opción futura para componentes concretos si el profiling demuestra que Python no cumple latencia o estabilidad**

En otras palabras:
- no conviene migrar el proyecto completo a C++ ahora,
- pero sí conviene dejar abierta una arquitectura compatible con módulos acelerados en C++ si más adelante hacen falta.

## Por qué no conviene decidir “C++ para todo” ahora

### 1. El proyecto todavía está en fase de definición y MVP
RestaurIA aún necesita cerrar:
- estados,
- eventos,
- pipeline base,
- dataset inicial,
- y validación operativa.

En esta fase, el coste de iteración importa más que exprimir el último milisegundo.

### 2. El stack ya está orientado a Python
El repositorio y la documentación ya apuntan a:
- Python,
- OpenCV,
- FastAPI,
- scikit-learn,
- PyTorch,
- y una arquitectura modular fácil de prototipar.

Mover el núcleo a C++ ahora aumentaría:
- complejidad de build,
- tiempo de desarrollo,
- coste de mantenimiento,
- y dificultad de integración con el resto del sistema.

### 3. Gran parte del trabajo pesado ya corre en código nativo
Aunque escribamos en Python:
- `cv2` ejecuta internamente mucho código nativo optimizado,
- `numpy` vectoriza operaciones,
- `scikit-learn` y otras librerías también aprovechan implementaciones compiladas,
- y OpenCV puede beneficiarse de IPP/SIMD si la instalación lo soporta.

Eso significa que Python no equivale automáticamente a lentitud en la parte crítica.

## Qué sí aporta C++ de verdad
C++ tiene valor real en ciertos casos:
- latencia extrema,
- control fino de memoria,
- integración con pipelines complejos de cámara,
- despliegues edge muy ajustados,
- o necesidad de exprimir CPU/GPU al máximo.

También aporta:
- acceso más directo a toda la API moderna de OpenCV,
- integración más natural con `cv::Mat`, `cv::VideoCapture`, `cv::warpPerspective`, `BackgroundSubtractorMOG2`, etc.,
- y mejor ergonomía si algún día se construye un servicio de visión muy optimizado o embebido.

## Qué aporta Python ahora mismo

### 1. Velocidad de iteración
Es la ventaja más importante en este momento.

Permite:
- probar pipelines visuales,
- cambiar features,
- ajustar reglas,
- depurar rápido,
- y conectar visión, eventos y ML clásico con mucho menos coste.

### 2. Mejor integración con el resto del proyecto
Python encaja mejor con:
- FastAPI,
- scripts de entrenamiento,
- notebooks,
- validación de datos,
- persistencia rápida,
- y prototipado de motor de decisión.

### 3. Menor complejidad operacional
Con Python evitamos de inicio:
- toolchains más pesados,
- compilación multiplataforma compleja,
- bindings internos antes de tiempo,
- y mayor fricción para experimentar.

## Recomendación de arquitectura

### Opción elegida para el proyecto
Construir el sistema así:
- **orquestación en Python**
- **visión clásica y ML en Python apoyados en librerías nativas**
- **módulos acelerados opcionales más adelante**

### Traducción práctica
Usar Python para:
- captura,
- adaptador video-to-observation,
- gestión de zonas,
- preprocesado clásico,
- segmentación baseline,
- motor de eventos,
- estado de mesa,
- API y dashboards,
- ML clásico y persistencia.

Reservar C++ para:
- un posible módulo de visión de alto rendimiento,
- una librería interna para múltiples cámaras,
- o un componente edge si el profiling demuestra cuello de botella real.

## Decisión específica por bloque

### Captura de vídeo
**Python**

Motivo:
- `cv2.VideoCapture` es suficiente para MVP y piloto temprano,
- integración rápida con archivos, webcam y RTSP,
- menor complejidad.

### HighGUI / herramienta de calibración
**Python**

Motivo:
- herramienta interna de laboratorio,
- no justifica C++ de entrada,
- suficiente para setup y debug.

### MOG2, contornos, homografía, warpPerspective
**Python primero**

Motivo:
- son operaciones ya implementadas en OpenCV nativo,
- desde Python el coste dominante muchas veces no está en la llamada sino en la arquitectura global.

### ML clásico de ETA
**Python**

Motivo:
- ecosistema mucho mejor,
- scikit-learn y similares encajan mejor que la MLL antigua de OpenCV,
- mayor mantenibilidad.

### Dashboard y backend
**Python**

Motivo:
- encaje natural con FastAPI y capa de producto.

### Posible núcleo futuro de visión edge
**C++ solo si hace falta**

Motivo:
- aquí sí puede tener sentido si se demuestra un cuello de botella serio en producción.

## Cuándo plantearse seriamente C++
No por intuición ni por prestigio técnico.

Solo si se cumple una de estas condiciones:
- Python no alcanza la latencia objetivo tras optimizar ROIs, frecuencia y pipeline,
- hay varias cámaras simultáneas y el coste por frame se dispara,
- el uso de CPU es inaceptable en hardware objetivo,
- el despliegue edge exige footprint y control más estrictos,
- o un profiling serio señala que un módulo concreto merece reescribirse.

## Qué no conviene hacer
- reescribir el proyecto entero en C++ “por si acaso”,
- mezclar Python y C++ demasiado pronto sin una frontera clara,
- construir bindings prematuros,
- o tomar `cv::Mat` como argumento suficiente para migrar todo.

## Estrategia correcta si algún día hace falta C++

### Paso 1
Perfilar el sistema real y localizar el cuello de botella.

### Paso 2
Aislar el módulo problemático.

### Paso 3
Reescribir solo ese módulo en C++.

### Paso 4
Exponerlo como:
- binario auxiliar,
- servicio local,
- o extensión enlazada,
sin contaminar toda la arquitectura.

## Nota sobre Qt y HighGUI
La integración con Qt puede ser interesante para herramientas internas más ricas.

Pero no cambia la decisión global del proyecto:
- no justifica mover todo a C++,
- y no sustituye la necesidad de separar herramienta técnica y dashboard final.

## Nota sobre cámaras inalámbricas
Que la cámara sea inalámbrica no obliga a C++.

Lo relevante es:
- protocolo de entrada,
- estabilidad del stream,
- latencia de red,
- resolución,
- y frecuencia real de procesamiento.

Si la cámara llega por RTSP o flujo similar, Python sigue siendo perfectamente válido para el MVP y piloto temprano.

## Regla de decisión final
La política recomendada para RestaurIA es:

1. construir en Python el sistema completo del MVP,
2. medir latencia real y estabilidad,
3. optimizar arquitectura y frecuencia,
4. y solo después evaluar C++ para piezas concretas si sigue habiendo un cuello de botella.

## Conclusión
La transición histórica de OpenCV hacia C++ moderno es importante y valiosa, pero no obliga a que RestaurIA se implemente entero en C++.

La decisión profesional correcta, hoy, es:
- **Python como base del producto**
- **C++ como opción táctica futura para acelerar módulos concretos**

Esto maximiza velocidad de desarrollo, coherencia del stack y capacidad de evolucionar sin cerrarnos la puerta al rendimiento cuando de verdad haga falta.
