# Transformaciones geométricas y rectificación

## Propósito
Definir cómo usar transformaciones de imagen y geometría para que RestaurIA pueda interpretar de forma más estable el espacio del restaurante, especialmente cuando la cámara observa la sala con perspectiva inclinada.

Este documento cubre:
- gradientes y bordes,
- detección geométrica,
- rectificación por homografía,
- imágenes integrales,
- y normalización de iluminación.

## Decisión técnica principal
No todas las transformaciones de este capítulo deben entrar en el MVP.

La prioridad real para RestaurIA es:
1. rectificar el plano útil cuando aporte valor claro,
2. estabilizar la lectura espacial de mesas y zonas,
3. y mejorar rendimiento y explicabilidad.

Por tanto, distinguimos:
- técnicas de **uso inmediato en MVP**,
- técnicas de **laboratorio o apoyo**,
- y técnicas de **fase posterior**.

## Problema que resuelve esta capa
Una cámara instalada en altura o en ángulo introduce:
- deformación de perspectiva,
- tamaños aparentes inconsistentes,
- zonas difíciles de delimitar,
- y ambigüedad al decidir si una persona está realmente dentro de una mesa o solo cerca.

La rectificación geométrica busca reducir ese problema.

## Lugar en la arquitectura
Esta capa pertenece a `services/vision/` y puede actuar:
- antes de extraer señales por ROI,
- o como transformación previa a la definición estable de zonas.

Flujo conceptual:

```text
frame original
  -> corrección geométrica opcional
  -> definición o transformación de zonas
  -> extracción de ROI / máscara
  -> preprocesado
  -> observaciones
```

## 1. Gradientes y detección de bordes

### Sobel
Útil para:
- detectar cambios abruptos de intensidad,
- resaltar bordes,
- y explorar contornos de mesas, sillas o siluetas.

### Scharr
Es una variante más precisa para kernels pequeños y puede ser útil cuando:
- se necesita mayor sensibilidad de borde,
- o Sobel introduce demasiado error en escala reducida.

### Regla práctica
En RestaurIA, Sobel o Scharr deben verse como herramientas de:
- exploración,
- depuración,
- o generación de señales auxiliares.

No deben ser el núcleo del MVP salvo que una prueba concreta demuestre que aportan robustez real.

## 2. Detector de bordes Canny

### Valor práctico
Canny es especialmente útil para:
- obtener contornos limpios,
- separar estructura fuerte de textura débil,
- apoyar calibración de zonas,
- y explorar geometría del entorno.

### Aplicación en RestaurIA
Uso recomendable en:
- laboratorio,
- calibración,
- detección visual de límites de mesa,
- y herramientas de setup.

Uso menos recomendable como lógica central de ocupación:
- por sí solo no basta para inferir presencia real,
- pero puede complementar otras señales.

## 3. Transformadas de Hough

### Líneas
Pueden ser útiles para:
- detectar alineaciones de mobiliario,
- inferir estructura del local,
- o validar orientación de cámara.

### Círculos
Pueden ser interesantes si en una fase posterior se quieren explorar:
- platos,
- vasos,
- u objetos redondos de servicio.

### Regla práctica
Las transformadas de Hough son útiles como herramientas de:
- análisis,
- setup,
- y laboratorio.

No deben cargarse sobre el MVP inicial salvo que exista un caso de uso concreto y medido.

## 4. Homografía y vista cenital

### Qué es lo importante aquí
La homografía permite mapear un plano observado con perspectiva a una representación rectificada.

En RestaurIA, esto es especialmente relevante para:
- el plano del suelo,
- zonas de paso,
- posición relativa de personas,
- y delimitación más estable de mesas si la cámara observa desde ángulo oblicuo.

### Valor para el proyecto
Una vista rectificada puede convertir preguntas complejas en comprobaciones más simples:
- si un punto cae dentro de una zona,
- si una trayectoria entra o sale,
- si una ocupación invade otra área,
- si una persona está realmente en una mesa o solo pasando cerca.

### Decisión para el MVP
La homografía **sí debe quedar contemplada desde ya**, pero como capacidad opcional.

Regla:
- si una cámara frontal simple y ROIs bien definidas resuelven el laboratorio, no forzar homografía de entrada;
- si el ángulo rompe claramente la precisión, introducir rectificación temprana.

### Recomendación práctica
Guardar por cámara:
- puntos de referencia,
- matriz de homografía si existe,
- versión rectificada de zonas si aplica.

## 5. Imágenes integrales

### Qué aportan
Permiten calcular sumas sobre regiones de forma muy rápida.

### Aplicación útil
Pueden ser valiosas para:
- densidad de píxeles activos,
- energía de movimiento en ROI,
- estimaciones rápidas de ocupación visual,
- y señales de bajo coste para varias mesas simultáneas.

### Decisión
No son obligatorias para arrancar, pero sí merecen quedar registradas como optimización prometedora para:
- muchas ROIs,
- hardware limitado,
- o fase de escalado.

## 6. Ecualización de histograma

### Qué problema ataca
Las diferencias de iluminación entre zonas pueden romper la estabilidad del pipeline.

### Uso recomendado
Puede mejorar robustez en:
- zonas oscuras,
- contraluces,
- cámaras con rango dinámico pobre,
- o escenas con luz muy desigual.

### Precaución
No debe aplicarse sin medir porque también puede:
- exagerar ruido,
- alterar textura útil,
- o volver menos interpretable la señal.

### Regla práctica
Usarla como herramienta de:
- laboratorio,
- comparación de pipelines,
- o fallback por cámara conflictiva.

## Qué técnicas entran en el MVP

### Sí, como candidatas realistas
- homografía opcional si la perspectiva lo exige,
- Canny para calibración y apoyo visual,
- gradientes como depuración o análisis auxiliar,
- normalización geométrica de zonas,
- y eventualmente reducción de coste con imágenes integrales si el baseline lo necesita.

### No como centro del MVP inicial
- Hough para objetos complejos,
- detección avanzada de círculos de platos,
- o pipelines geométricos excesivos sin evidencia de mejora.

## Configuración persistente por cámara
La configuración del sistema debe poder almacenar por cámara:
- resolución base,
- puntos de calibración,
- matriz de transformación,
- zonas en coordenadas originales,
- zonas en coordenadas rectificadas si existen,
- y notas de validación de calibración.

## Señales que esta capa puede producir
Además del frame transformado, esta capa puede producir:
- mapa de bordes,
- gradiente,
- frame rectificado,
- métricas geométricas,
- pertenencia punto-zona más estable,
- y energía local acumulada por región.

## Relación con ROIs y mesas
La rectificación no sustituye a las ROIs. Las mejora.

Combinación recomendada:
- primero definir si la cámara necesita rectificación,
- después extraer o transformar las zonas,
- y finalmente procesar cada ROI en un espacio más estable.

## Recomendaciones para la fase de laboratorio
- comparar pipeline con y sin rectificación,
- medir mejora real de ocupación por mesa,
- validar si la homografía simplifica pertenencia a zona,
- registrar errores producidos por mala calibración,
- y no asumir que una transformación más compleja siempre mejora el resultado.

## Qué no conviene hacer todavía
- añadir homografía a todas las cámaras por defecto,
- introducir transformaciones complejas sin dataset de prueba,
- optimizar antes de demostrar el beneficio,
- o mezclar calibración geométrica con lógica de negocio.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/09_rois_zonas_y_operadores_de_imagen.md`
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/04_software_y_devops/08_highgui_herramienta_de_calibracion.md`
- `docs/03_datos_y_ml/16_calibracion_de_camara_y_precision_metrica.md`

## Conclusión
El valor de este capítulo para RestaurIA está en convertir una cámara inclinada en una fuente de información espacial más estable y medible.

La pieza estratégica aquí es la rectificación:
- no como sofisticación gratuita,
- sino como herramienta para reducir ambigüedad,
- mejorar pertenencia a zona,
- y preparar el sistema para pasar del laboratorio a un entorno real con geometría menos amable.
