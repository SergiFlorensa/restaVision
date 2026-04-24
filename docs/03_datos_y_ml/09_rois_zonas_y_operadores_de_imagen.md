# ROIs, zonas y operadores de imagen

## Propósito
Traducir los conceptos estructurales de OpenCV sobre tipos de datos, matrices, subregiones y operadores de imagen a una estrategia práctica para RestaurIA.

Este documento se centra en una idea clave para el MVP:
- no analizar toda la imagen por igual,
- sino segmentarla en zonas útiles,
- especialmente por mesa,
- y operar sobre esas subregiones con el menor coste posible.

## Decisión técnica principal
Aunque el capítulo original habla en términos de `CvMat`, `IplImage`, `CvRect`, `CvPoint` y acceso manual con punteros, en RestaurIA se usará la capa moderna:
- `cv2`
- `numpy.ndarray`
- slicing de arrays
- estructuras Python tipadas para configuración y dominio

La lógica sigue siendo la misma:
- una imagen es una matriz,
- una mesa es una subregión,
- y la eficiencia depende de procesar solo lo necesario.

## Tipos conceptuales que sí necesitamos en el dominio

### Punto
Uso:
- coordenadas,
- centroides,
- trayectorias,
- anclajes visuales.

En implementación moderna:
- tuplas `(x, y)`,
- dataclasses,
- o modelos `pydantic` según la capa.

### Tamaño
Uso:
- normalización de resolución,
- validación de entrada,
- consistencia entre cámara y configuración.

### Rectángulo
Uso:
- definición simple de mesa o subzona,
- recorte rápido de región,
- overlays y depuración visual.

Representación visual típica:
- dos esquinas opuestas,
- color por estado,
- grosor configurable,
- o relleno si se necesita destacar la zona.

### Polígono
Uso:
- zonas no rectangulares,
- mesas irregulares,
- adaptación a perspectiva real del local.

Principio:
- el rectángulo puede servir para el MVP temprano,
- pero el modelo debe dejar abierta la puerta a polígonos.

### Escalar / color
Uso:
- overlays de estado,
- trazado de cajas y zonas,
- capas visuales de depuración y dashboard.

## Las zonas como unidad operativa
En RestaurIA, una zona no es solo geometría. Es una unidad de decisión.

Una zona debería poder representar:
- una mesa,
- un área de paso,
- una cola,
- una caja,
- o una región de limpieza.

Por eso, la geometría debe ir acompañada de semántica:
- `zone_id`
- `zone_type`
- `camera_id`
- `label`
- `capacity`
- `geometry`

## ROI como mecanismo central del MVP

### Qué significa aquí ROI
Una ROI es la región del frame sobre la que queremos trabajar de forma selectiva.

En el MVP, la ROI será la base para:
- estimar ocupación de mesa,
- contar personas dentro de una zona,
- medir cambio respecto a fondo o estado previo,
- y limitar coste computacional por mesa.

### Por qué es crítica
Sin ROI:
- se procesa ruido irrelevante,
- aumentan falsos positivos,
- sube la latencia,
- y se complica la explicación del sistema.

Con ROI:
- el análisis se vuelve local,
- trazable,
- más barato,
- y más fácil de depurar.

## Estrategia recomendada para ROIs

### Fase 1
Usar ROIs rectangulares simples por mesa.

Ventajas:
- implementación rápida,
- depuración sencilla,
- fácil persistencia.

### Fase 2
Permitir máscaras o polígonos por zona.

Ventajas:
- mejor ajuste a perspectiva,
- menos ruido por zonas adyacentes,
- más precisión operativa.

## Cómo se representa una ROI en la implementación moderna
En Python con `numpy`, la ROI no necesita copiar datos si se trabaja con slices.

Ejemplo conceptual:

```python
roi = frame[y:y+h, x:x+w]
```

Esto es importante porque:
- reduce coste,
- evita duplicaciones innecesarias,
- y encaja con el principio del capítulo de crear vistas sobre la imagen en lugar de copiarla.

### Equivalencia con la API clásica
En la API clásica de OpenCV en C, esta idea se expresaba con:
- `CvRect` para definir el área,
- `cvSetImageROI()` para activar la región,
- y `cvResetImageROI()` para volver al frame completo.

En RestaurIA, la traducción moderna recomendada es:
- guardar la geometría de zona de forma explícita,
- recortar con slicing sobre `numpy.ndarray`,
- y evitar modificar el estado global del frame si no es necesario.

## Monitoreo de una mesa específica

### Paso 1. Definir la geometría de la mesa
La mesa debe quedar definida por:
- coordenadas,
- tamaño o polígono,
- identificador,
- y relación con la cámara.

Para el MVP temprano, un rectángulo es suficiente si la escena es simple.

### Paso 2. Extraer la vista local
La forma preferida en Python es:

```python
mesa_view = frame[y:y+h, x:x+w]
```

Esto crea una vista local de la mesa sobre la que se puede aplicar:
- sustracción de fondo,
- histogramas,
- máscaras,
- contornos,
- o detección de personas.

### Paso 3. Procesar solo la mesa
Todas las funciones posteriores deben operar sobre `mesa_view` o sobre una máscara derivada de esa zona.

Ventajas:
- ahorro de CPU,
- menor ruido,
- menos falsos positivos por actividad ajena,
- y mejor trazabilidad.

### Paso 4. Mantener el frame completo intacto
En la implementación moderna, no hace falta “resetear” la ROI como en la API C si trabajamos con slices locales.

Eso es mejor porque:
- evita efectos laterales,
- simplifica el código,
- y permite seguir usando el frame completo para overlays o depuración.

## Estrategia recomendada de implementación

### Opción baseline
Procesado secuencial por mesa:
- iterar zonas activas,
- extraer `mesa_view`,
- ejecutar pipeline local,
- guardar observación.

Esta opción es suficiente para:
- laboratorio,
- una o pocas mesas,
- y primer MVP.

### Opción de escalado temprano
Mantener varias vistas activas sobre el mismo frame usando slices o estructuras ligeras por zona.

La idea conceptual es la misma que el “truco” clásico de múltiples encabezados:
- varias vistas,
- mismos datos base,
- sin copia masiva de memoria.

En Python, esto se consigue más naturalmente con:
- slices de `numpy`,
- objetos `ZoneView`,
- o paquetes de ROI precalculadas por frame.

## Cuándo no usar solo ROI rectangulares
El recorte rectangular puede fallar si:
- dos mesas están muy juntas,
- la cámara tiene mucha perspectiva,
- hay actividad de pasillo dentro del rectángulo,
- o el mobiliario real no encaja bien en un bbox simple.

En esos casos, conviene pasar a:
- polígonos,
- máscaras por zona,
- o rectificación geométrica previa.

## Relación con la herramienta de setup
La geometría de la mesa debe poder capturarse desde la herramienta de calibración mediante:
- clics de ratón,
- arrastre de rectángulo,
- edición posterior,
- y persistencia en archivo.

## Regla de diseño
En RestaurIA, la ROI no debe ser un truco local de OpenCV oculto dentro del procesamiento.
Debe ser una entidad explícita del sistema:
- persistida,
- trazable,
- editable,
- y vinculada a la lógica de negocio de cada mesa.

## Operadores de imagen útiles para el MVP

### Conversión de color
Uso:
- pasar de BGR a gris,
- o a HSV si la robustez a iluminación lo exige.

Aplicación:
- simplificar ciertas comparaciones,
- reducir sensibilidad al ruido de color,
- preparar máscaras.

### Comparación entre estados
Uso:
- comparar ROI actual con referencia,
- medir cambio suficiente para inferir ocupación o transición.

Aplicación:
- baseline de ocupación,
- variación temporal,
- detección simple de actividad.

### Mezcla ponderada
Uso:
- superponer estado visual sobre vídeo,
- mostrar color de zona sin perder la imagen base.

Aplicación:
- dashboard de depuración,
- vídeo anotado,
- modo laboratorio.

### Dibujo de rectángulos, polígonos y texto
Uso:
- mostrar zonas,
- imprimir estado,
- mostrar ETA,
- visualizar score o confianza.

Principio:
- si el sistema no puede mostrar por qué cree algo, será difícil depurarlo y confiar en él.

## Pipeline mínimo por ROI
Para cada mesa o zona, el flujo mínimo podría ser:

```text
frame
  -> extraer ROI
  -> preprocesar ROI
  -> calcular señales locales
  -> inferir observación de zona
  -> emitir observación estructurada
```

Las señales locales pueden incluir:
- diferencia respecto a referencia,
- cantidad de movimiento,
- detecciones de persona dentro de zona,
- porcentaje de máscara activa,
- tiempo desde último cambio.

## Configuración persistente del local

### Qué debe guardarse
La configuración del restaurante debe persistir fuera del código.

Al menos:
- cámaras,
- zonas,
- mesas,
- tipo de geometría,
- coordenadas,
- nombres,
- capacidad,
- activación o desactivación.

### Formatos razonables
Para el MVP:
- YAML o JSON son suficientes.

Ventaja:
- fáciles de versionar,
- fáciles de editar,
- fáciles de cargar al iniciar.

### Recomendación de diseño
No mezclar geometría hardcodeada en el código fuente.

La calibración del local debe poder:
- cargarse,
- validarse,
- exportarse,
- y actualizarse sin tocar lógica de negocio.

## Relación con el esquema de datos
Este documento refuerza especialmente:
- `zones.polygon_definition`
- `tables.zone_id`
- y cualquier futura tabla de configuraciones de cámara o calibración.

## Rendimiento y latencia

### Lo que sí aporta rendimiento
- recortar por ROI,
- reducir resolución cuando convenga,
- evitar copias innecesarias,
- operar con arrays ya existentes,
- y limitar cálculo al área relevante.

### Lo que no conviene hacer de entrada
- microoptimización manual prematura,
- acceso pixel a pixel salvo necesidad clara,
- código opaco por ahorrar milisegundos sin medir,
- o reimplementar primitivas que OpenCV/Numpy ya resuelven bien.

## Sobre acceso eficiente a memoria
El capítulo insiste correctamente en que el acceso genérico píxel a píxel es costoso.

Aplicación moderna al proyecto:
- preferir operaciones vectorizadas con `numpy`,
- usar funciones nativas de `cv2`,
- evitar bucles Python sobre píxeles,
- y reservar la optimización de bajo nivel para casos medidos.

## Depuración visual
El sistema debe poder producir una vista anotada con:
- ROI dibujadas,
- identificador de mesa,
- estado estimado,
- confianza,
- conteo de personas,
- y ETA si existe.

Esto es esencial para:
- validar reglas,
- comparar hipótesis,
- y explicar comportamiento del sistema.

### Regla específica para mesas rectangulares
Si la mesa se modela como `roi_bbox`, el sistema debe poder:
- dibujar el rectángulo,
- etiquetar la mesa,
- cambiar color según estado,
- y mantener la geometría coherente con la configuración persistida.

## Recomendación de implementación para el repositorio

### `services/vision/`
Responsable de:
- cargar configuración geométrica,
- extraer ROIs,
- aplicar preprocesado,
- producir observaciones locales.

### `infra/` o configuración externa
Responsable de:
- almacenar los archivos YAML/JSON del local.

### `apps/worker/`
Responsable de:
- iterar sobre zonas activas,
- invocar el pipeline por ROI,
- consolidar observaciones.

## Conclusión
El valor profundo de este capítulo para RestaurIA es que convierte el frame completo en un conjunto de unidades operativas manejables.

La combinación de:
- ROIs por mesa,
- geometría persistente,
- operadores simples sobre subregiones,
- y depuración visual,
es la base práctica para pasar de “capturar vídeo” a “entender qué está pasando en cada mesa”.
