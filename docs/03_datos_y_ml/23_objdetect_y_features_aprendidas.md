# Objdetect y features aprendidas

## Propósito
Definir cómo encajan en RestaurIA los detectores clásicos de objetos y las features aprendidas o extraídas de imagen para:
- conteo de personas,
- detección de objetos sobre mesa,
- clasificación de estados visuales,
- y validación contextual de observaciones.

Este documento toma como referencia el módulo `objdetect` y los enfoques clásicos de OpenCV, pero los traduce a la estrategia real y actual del proyecto.

## Decisión técnica principal
Los enfoques clásicos de detección como:
- Haar cascades,
- HOG + clasificadores,
- y features estadísticas de imagen,
tienen valor para:
- laboratorio,
- baseline histórico,
- casos de uso controlados,
- y ciertos detectores de objetos específicos.

Pero no deben considerarse automáticamente la base moderna principal del sistema.

Regla de proyecto:
- usar estas técnicas si aportan valor real y medible,
- no por inercia histórica de OpenCV.

## 1. Haar cascades

### Qué aportan
Las cascadas son rápidas y fáciles de probar cuando existe:
- una estructura visual relativamente rígida,
- un objeto con patrón claro,
- o un caso de uso simple y bien encuadrado.

### Valor potencial en RestaurIA
Pueden servir para:
- prototipos rápidos,
- pruebas sobre objetos muy concretos,
- o estudios exploratorios de detección clásica.

### Limitaciones
No son una buena base moderna para:
- conteo robusto de personas en sala,
- variación de ángulo,
- oclusiones,
- y condiciones reales no controladas.

### Decisión
Mantenerlas como referencia histórica o herramienta de laboratorio.
No tomarlas como vía principal de conteo del producto.

## 2. HOG

### Qué aporta
HOG describe la imagen a partir de orientaciones de gradiente y es especialmente útil para:
- estructura corporal,
- siluetas,
- y detección de peatones o personas.

### Valor para el proyecto
Puede ser una opción clásica más seria que Haar para:
- detección de personas en movimiento,
- validación de masa humana,
- o clasificación geométrica de regiones activas.

### Limitaciones
Sigue teniendo límites en:
- escenas muy densas,
- oclusiones,
- perspectivas complejas,
- y entornos con mucha variabilidad.

### Decisión
HOG sí merece quedar documentado como un posible baseline clásico de detección humana, si se necesita una alternativa ligera y explicable.

No debe imponerse como primera elección sin medir frente a enfoques más actuales o frente a una lógica clásica bien resuelta por ROI.

## 3. Histogramas como features

### Qué aportan
Los histogramas pueden actuar como vectores de características para alimentar clasificadores.

### Valor para RestaurIA
Esto es útil cuando queremos:
- convertir una ROI en variables agregadas,
- reforzar una clasificación visual,
- o pasar de reglas manuales a aprendizaje supervisado ligero.

### Aplicación razonable
Usar histogramas como features para:
- diferenciar mesa vacía de mesa alterada,
- apoyar clasificación de fases visuales,
- o detectar patrones de apariencia estables.

### Decisión
Sí tienen sentido como features auxiliares del sistema.
No deben ser la única base de la semántica visual.

## 3.1. Objetos de servicio: platos, cubiertos y cuenta

### Por qué importa
Para RestaurIA, detectar objetos de servicio puede reforzar estados como:
- `servida`,
- `consumiendo`,
- `finalizando`,
- y `lista_para_desbarasar`.

### Qué tipo de problema es realmente
No es el mismo problema que:
- contar personas,
- detectar presencia humana,
- o segmentar movimiento general.

Aquí hablamos de objetos:
- más pequeños,
- a veces parcialmente ocluidos,
- con mucha variación visual,
- y muy dependientes del ángulo de cámara.

### Estrategia recomendada
No empezar por un detector complejo por inercia.

Orden recomendado:
- primero `template matching` o reglas visuales simples si la vista es muy cenital y controlada,
- después clasificación ligera con features agregadas si hace falta distinguir fases visuales,
- y solo más tarde un detector entrenado clásico o moderno si el caso de uso demuestra retorno real.

### Features razonables
Si se explora clasificación de objetos o fases de servicio, las features más razonables son:
- HOG o gradientes para forma general,
- histogramas de color y brillo por ROI,
- área y contornos de blobs relevantes,
- y combinaciones de descriptores sencillos sobre subzonas de mesa.

### Qué evitar como primera apuesta
- entrenar cascadas Haar para cualquier objeto por simple disponibilidad,
- detectar cubiertos finos como requisito duro temprano,
- o prometer reconocimiento robusto de vajilla en condiciones no controladas.

### Decisión
La detección de objetos de servicio queda documentada como capacidad de valor real, pero no como núcleo del MVP temprano.

Su mejor papel inicial es:
- reforzar transiciones de estado,
- generar evidencias auxiliares,
- y apoyar laboratorio de fases de servicio.

## 4. Contexto como señal de validación

### Qué aporta
Una detección aislada vale menos que una detección contextualizada.

### Valor para el proyecto
RestaurIA puede beneficiarse de reglas o modelos que incorporen contexto como:
- cercanía a mesa,
- presencia de sillas,
- zona operativa,
- trayectoria previa,
- y coherencia con el estado actual.

### Ejemplo útil
Una región parecida a una persona:
- cerca de una mesa,
- con trayectoria de entrada,
- y coherente con el contexto visual,
tiene más credibilidad que una silueta aislada sin lógica espacial.

### Decisión
El contexto debe formar parte de la validación de observaciones.
Esto encaja especialmente bien con la capa de:
- eventos,
- reglas,
- y estados de mesa.

## 5. Clasificación de formas y gestos

### Qué aporta
Los descriptores de gradiente y forma pueden servir para detectar patrones más ricos que la ocupación simple.

### Valor potencial
En fases posteriores podrían apoyar:
- gestos,
- posturas,
- movimientos específicos,
- o transiciones más finas de comportamiento.

### Riesgo
No conviene prometer esto en el MVP porque:
- requiere más datos,
- más validación,
- y una semántica mucho más delicada.

### Decisión
Registrar como línea futura de investigación, no como promesa operativa temprana.

## 6. Flujo recomendado de uso

### Caso 1. Detección humana clásica
ROI o frame
-> extracción de descriptor
-> clasificador o detector
-> bounding boxes o score
-> validación espacial y temporal

### Caso 2. Clasificación de estado visual
ROI
-> features agregadas (histograma, área, blobs, actividad)
-> clasificador supervisado
-> score de estado
-> integración con máquina de estados

### Caso 3. Objetos de servicio sobre mesa
ROI de mesa o subROI
-> preprocesado
-> descriptor simple o plantilla
-> score de presencia de objeto
-> validación temporal
-> refuerzo de estado de servicio

## Qué entra realmente en el proyecto

### Sí entra como posibilidad razonable
- HOG como baseline clásico de detección humana si se necesita,
- histogramas y features agregadas para clasificación ligera,
- detección prudente de objetos de servicio en escenarios controlados,
- y validación contextual de observaciones.

### Queda como apoyo secundario
- Haar cascades,
- detectores rígidos históricos,
- detectores clásicos de cubiertos o vajilla como promesa general,
- y clasificación de gestos o señales complejas.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/12_histogramas_y_matching_visual.md`
- `docs/03_datos_y_ml/18_ml_clasico_y_modelado_predictivo.md`
- `docs/03_datos_y_ml/15_tracking_y_movimiento_temporal.md`
- `docs/03_datos_y_ml/21_autosetup_geometrico_y_asignacion_espacial.md`
- `docs/04_software_y_devops/11_decision_python_vs_cpp_para_vision.md`

## Conclusión
El módulo `objdetect` y las features aprendidas aportan una capa intermedia muy valiosa entre:
- visión clásica pura,
- y modelos más sofisticados.

En RestaurIA, su papel correcto es:
- reforzar observaciones,
- aportar detectores clásicos cuando convenga,
- y permitir clasificaciones ligeras basadas en features útiles,
sin convertir herramientas históricas de OpenCV en dogma de diseño.
