# Segmentación avanzada y restauración

## Propósito
Definir qué técnicas avanzadas de limpieza y segmentación visual pueden aportar valor a RestaurIA cuando el entorno real sea más exigente que el laboratorio inicial.

Este documento cubre:
- denoising avanzado,
- segmentación precisa de primer plano,
- reparación visual,
- uso intensivo de imágenes integrales,
- y gestión robusta de memoria a nivel de imagen.

## Decisión técnica principal
Estas técnicas no deben entrar por defecto en el MVP temprano.

Su papel correcto es:
- mejorar robustez en cámaras difíciles,
- resolver casos visuales que el baseline clásico no pueda manejar,
- y quedar preparadas como toolkit de escalado.

Regla:
- primero baseline simple y medible,
- después técnicas avanzadas solo si el fallo real lo justifica.

## Adaptación al proyecto
Aunque el libro describe estos conceptos desde OpenCV 2.x en C++, en RestaurIA se aplicarán según la política ya fijada:
- implementación principal en Python,
- usando wrappers modernos de OpenCV (`cv2`),
- y solo planteando C++ si el profiling demuestra un cuello de botella real.

## 1. Eliminación de ruido avanzada

### Qué problema resuelve
Una cámara inalámbrica o una cámara con poca luz puede introducir:
- granulado,
- ruido cromático,
- puntos aislados,
- y degradación que rompe segmentación y contornos.

### Fast Non-Local Means
El denoising tipo `fastNlMeansDenoising` o `fastNlMeansDenoisingColored` es útil porque:
- preserva mejor estructura que filtros simples,
- aprovecha redundancia visual de la escena,
- y puede limpiar ruido sin destruir tanto detalle útil.

### Cuándo merece la pena
Usarlo cuando:
- la señal de cámara sea claramente ruidosa,
- la morfología y el suavizado simple no basten,
- o el granulado esté degradando de forma real la segmentación.

### Cuándo no conviene
No introducirlo de entrada si:
- la cámara ya ofrece señal limpia,
- el coste de cómputo es alto para el hardware objetivo,
- o el baseline simple ya funciona bien.

### Decisión para RestaurIA
Debe quedar como herramienta de mejora por cámara problemática, no como paso fijo universal.

## 2. GrabCut

### Qué aporta
`grabCut` puede separar primer plano y fondo con mucha más precisión que una sustracción simple si se parte de una región aproximada.

### Valor potencial
Es especialmente interesante para:
- experimentos de segmentación fina,
- depuración de escenas difíciles,
- o generación semiautomática de máscaras de calidad.

### Limitaciones
No es una buena base para el MVP en tiempo real por:
- coste,
- necesidad de inicialización razonable,
- y mayor complejidad operativa.

### Decisión
Usarlo como:
- herramienta de laboratorio,
- ayuda para construir dataset,
- o técnica de validación visual.

No como núcleo del pipeline online de ocupación temprana.

## 3. Inpainting

### Qué problema resuelve
Puede reparar:
- manchas persistentes,
- artefactos locales,
- zonas dañadas de imagen,
- o ciertos elementos estáticos no deseados.

### Valor real en RestaurIA
Su utilidad principal no está en la lógica de ocupación, sino en:
- limpieza visual de material de debug,
- reparación de zonas pequeñas dañadas,
- o mejora estética puntual de una vista técnica.

### Decisión
No debe formar parte del núcleo de visión ni de decisiones de negocio.
Debe considerarse utilidad auxiliar, muy secundaria.

## 4. Imágenes integrales

### Qué aportan
Permiten calcular sumas de subregiones rectangulares en tiempo constante.

### Valor para RestaurIA
Son especialmente valiosas cuando:
- hay muchas mesas,
- muchas consultas rectangulares por frame,
- o se quiere calcular rápidamente densidad de actividad por ROI.

### Aplicaciones razonables
- suma de píxeles activos,
- densidad de movimiento,
- energía visual por mesa,
- señales rápidas para priorización.

### Decisión
Sí merecen estar registradas como optimización importante de escalado, especialmente si el número de mesas crece.

## 5. Gestión robusta de memoria con imágenes modernas

### Idea importante
La transición de la API C a `cv::Mat` resolvió muchos problemas históricos de memoria manual.

### Adaptación a Python
En RestaurIA esto se traduce a trabajar con:
- `numpy.ndarray`,
- referencias compartidas,
- slices,
- y disciplina sobre copias y buffers.

### Principio operativo
Aunque Python simplifica la memoria respecto a C:
- sigue siendo fácil degradar el sistema si se duplican frames innecesariamente,
- se guardan buffers sin límite,
- o se encadenan copias ocultas.

### Regla de proyecto
Mantener siempre claro:
- qué frame es original,
- qué artefactos son vistas,
- qué objetos son copias reales,
- y cuánto tiempo viven en memoria.

## Qué entra de verdad en el proyecto

### Sí entra como herramienta útil
- imágenes integrales para optimización futura,
- denoising avanzado como mejora por cámara problemática,
- y buena disciplina de memoria con arrays y vistas.

### Se deja como exploración
- GrabCut para segmentación fina offline,
- inpainting como utilidad auxiliar,
- y cualquier técnica costosa que no mejore directamente ocupación, eventos o ETA.

## Orden correcto de adopción

### Paso 1
Baseline clásico:
- ROI,
- preprocesado simple,
- sustracción de fondo,
- contornos,
- señales por mesa.

### Paso 2
Si falla por ruido:
- evaluar denoising avanzado.

### Paso 3
Si la escala lo exige:
- introducir imágenes integrales.

### Paso 4
Si hay necesidad de máscara precisa o dataset mejor:
- usar GrabCut en laboratorio.

## Riesgos a vigilar
- añadir demasiado coste al pipeline online,
- ocultar problemas de cámara con filtros caros,
- mejorar la estética pero no la métrica,
- y complicar la trazabilidad del sistema.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`
- `docs/04_software_y_devops/10_estrategia_de_latencia_y_rendimiento.md`
- `docs/04_software_y_devops/11_decision_python_vs_cpp_para_vision.md`

## Conclusión
Estas técnicas avanzadas pueden aportar mucho valor, pero solo si se introducen con orden.

En RestaurIA, su función correcta es fortalecer el sistema cuando el entorno real lo exija, no inflar el MVP prematuramente.

La prioridad sigue siendo:
- señal simple,
- explicable,
- rápida,
- y suficiente para tomar buenas decisiones operativas.
