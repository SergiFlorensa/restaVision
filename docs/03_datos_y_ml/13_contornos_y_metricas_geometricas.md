# Contornos y métricas geométricas

## Propósito
Definir cómo usar contornos y métricas geométricas para transformar una máscara binaria o una región activa en entidades visuales medibles dentro de RestaurIA.

Este documento cubre:
- extracción de contornos,
- filtrado por tamaño y forma,
- relación espacial con zonas de mesa,
- y generación de señales geométricas útiles para ocupación y actividad.

## Decisión técnica principal
En RestaurIA, los contornos deben usarse como una capa intermedia entre:
- la máscara procesada,
- y la observación de zona.

No sustituyen a:
- detección de personas,
- tracking,
- ni lógica temporal,
pero son muy valiosos para:
- medir área activa,
- eliminar ruido,
- verificar pertenencia espacial,
- y convertir “manchas” en objetos razonables.

## Adaptación a la API moderna
El capítulo original trabaja con:
- `CvMemStorage`
- `CvSeq`
- `cvFindContours`

En la implementación moderna del proyecto trabajaremos con:
- `cv2.findContours`
- arrays y estructuras Python,
- y manejo de memoria implícito de Python/OpenCV.

### Consecuencia importante
No necesitaremos `CvMemStorage` explícito, pero sí debemos mantener la misma disciplina conceptual:
- no retener resultados innecesarios,
- limpiar estructuras por iteración,
- y no dejar crecer memoria o buffers sin control.

## Lugar en la arquitectura
Esta capa pertenece a `services/vision/` y se sitúa después del preprocesado.

Flujo conceptual:

```text
ROI
  -> preprocesado
  -> máscara binaria
  -> contornos / blobs
  -> métricas geométricas
  -> observación de zona
```

## Qué aporta un contorno en RestaurIA
Un contorno permite tratar una región activa como objeto geométrico con propiedades cuantificables.

Eso abre la puerta a calcular:
- área,
- bounding box,
- centroide,
- forma aproximada,
- pertenencia a una mesa,
- y estabilidad temporal.

## Casos de uso realistas para el MVP

### 1. Filtrado de ruido por tamaño
Uso:
- descartar regiones demasiado pequeñas,
- ignorar artefactos de iluminación,
- y quedarnos con blobs que tengan tamaño razonable.

### 2. Área ocupada por ROI
Uso:
- sumar área de contornos relevantes,
- estimar masa visual activa,
- reforzar señal de ocupación.

### 3. Bounding boxes de actividad
Uso:
- encapsular regiones activas,
- superponerlas en modo debug,
- comparar su posición con la geometría de la mesa.

### 4. Verificación de pertenencia a zona
Uso:
- decidir si el centroide o los puntos principales del contorno están dentro de la zona,
- reducir confusión entre mesa y zona adyacente.

### 5. Segmentación de blobs
Uso:
- separar actividad principal de pequeños residuos,
- estimar si una región compacta puede corresponder a persona sentada o ruido residual.

## Extracción de contornos

### Modo de recuperación
Para el MVP, el enfoque más razonable suele ser:
- recuperar contornos externos para actividad principal,
- y evitar jerarquías excesivas salvo necesidad clara.

### Jerarquía completa
Puede ser útil más adelante si se exploran:
- objetos dentro de zonas,
- relaciones padre-hijo,
- o análisis más detallado sobre mesa y elementos contenidos.

Ejemplo conceptual útil para RestaurIA:
- contorno principal de una región de mesa o masa ocupante,
- y contornos hijos asociados a objetos o regiones contenidas si la escena y la máscara lo permiten.

### Regla práctica
Empezar simple:
- contorno externo,
- aproximación eficiente,
- y métricas básicas.

## Aproximación poligonal

### Valor práctico
Simplificar contornos ruidosos puede ayudar a:
- reducir coste,
- estabilizar forma,
- y mejorar interpretabilidad.

### Uso recomendado
Aplicarlo cuando:
- la máscara genere contornos demasiado dentados,
- o interese comparar formas de forma más robusta.

### Precaución
No simplificar tanto que se pierda la semántica útil del blob.

## Métricas geométricas prioritarias

### Área
Debe ser una de las primeras métricas del MVP.

Sirve para:
- filtrar ruido,
- estimar ocupación,
- y diferenciar actividad residual de masa relevante.

### Bounding rectangle
Muy útil para:
- overlays,
- depuración,
- estimación rápida de ocupación visual,
- y comparación espacial con mesa/zona.

### Centroide o punto representativo
Útil para:
- comprobar pertenencia a zona,
- rastrear desplazamiento local,
- y simplificar decisiones geométricas.

### Perímetro y compactación
Pueden explorarse más adelante si aportan robustez para distinguir blobs humanos de ruido irregular.

## Point-in-polygon y relación espacial

### Valor para RestaurIA
Saber si un punto está dentro de una mesa o zona es extremadamente útil.

Aplicaciones:
- centroide dentro/fuera,
- puntos de interés en zona,
- intersección entre blob y geometría de mesa,
- y validación de ocupación real frente a cercanía accidental.

### Principio práctico
Una buena parte de la lógica espacial del MVP puede expresarse como:
- “¿está dentro?”
- “¿cuánto solapa?”
- “¿cuánto tiempo lleva dentro?”

## Matching de formas

### Valor potencial
La comparación de formas o descriptores como momentos puede ayudar a:
- distinguir blobs compactos de patrones extraños,
- explorar siluetas humanas sentadas,
- o detectar si una región es demasiado atípica.

### Decisión
No debe ser base del MVP inicial.

Puede registrarse como línea de exploración si:
- las máscaras son suficientemente limpias,
- y existe evidencia de que mejora la discriminación frente a ruido o mobiliario.

### Momentos invariantes
Los descriptores invariantes de forma pueden ser útiles para:
- comparar siluetas compactas,
- estudiar patrones de ocupación repetidos,
- o reforzar que una región relevante sigue siendo una entidad parecida aunque cambie ligeramente de tamaño u orientación.

Decisión:
- mantenerlos como exploración posterior,
- no como requisito del MVP.

## Señales que esta capa puede producir
- número de contornos relevantes,
- área total activa,
- área del mayor contorno,
- bounding box principal,
- centroide principal,
- porcentaje de solape con zona,
- dispersión de contornos,
- estabilidad geométrica entre frames.

## Cómo combinar contornos con otras señales
Los contornos no deben operar solos.

Combinación recomendada con:
- porcentaje de píxeles activos,
- histogramas de cambio visual,
- referencia de mesa vacía,
- detección de personas si existe,
- y consistencia temporal.

## Estrategia baseline recomendada

```text
ROI
  -> preprocesado
  -> máscara binaria
  -> extracción de contornos externos
  -> filtrado por área mínima
  -> cálculo de bounding box y centroide
  -> verificación de pertenencia a zona
  -> generación de señales geométricas
```

## Riesgos a vigilar
- contornos rotos por mala máscara,
- blobs unidos artificialmente,
- sombras convertidas en regiones activas,
- contornos de objetos pequeños sobre mesa,
- y sobreinterpretación geométrica sin contexto temporal.

## Recomendaciones de laboratorio
- visualizar contornos y bounding boxes sobre la ROI,
- medir qué área mínima elimina ruido sin perder ocupación real,
- guardar ejemplos donde dos personas se fusionan en un solo blob,
- y validar pertenencia a zona en casos límite de borde o cruce.

## Qué entra en el MVP
- extracción de contornos sobre máscara limpia,
- filtrado por área mínima,
- bounding box principal,
- centroide,
- relación dentro/fuera de zona,
- y uso en overlays de depuración.

## Qué se deja para después
- matching de forma avanzado,
- jerarquías complejas de contornos,
- clasificación por descriptor geométrico sofisticado,
- y lógica de objetos secundarios sobre mesa como eje principal.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/03_datos_y_ml/12_histogramas_y_matching_visual.md`

## Conclusión
El valor de este capítulo para RestaurIA está en que convierte una región activa en un objeto geométrico interpretable.

Eso permite pasar de:
- “hay píxeles blancos”
a
- “hay una masa relevante dentro de esta mesa, con tal área, tal posición y tal estabilidad”.

Esa transición es muy importante para construir una observación visual que luego pueda alimentar estados y eventos del sistema.
