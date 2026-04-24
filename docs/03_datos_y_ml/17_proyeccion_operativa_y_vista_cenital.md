# Proyección operativa y vista cenital

## Propósito
Definir cómo usar proyecciones geométricas para convertir la imagen de cámara en una representación operativa más útil del restaurante, especialmente mediante:
- vista de pájaro,
- reproyección de información al vídeo,
- y preparación para geometría espacial más rica en fases futuras.

## Decisión técnica principal
La `vista cenital` o `bird’s-eye view` es la capacidad con mayor valor práctico inmediato de este capítulo para RestaurIA.

En cambio:
- reproyección avanzada 3D,
- estimación automática de pose compleja,
- y visión estéreo,
deben registrarse como líneas de evolución, no como requisitos del MVP inicial.

## Problema que resuelve
Una cámara fija en perspectiva oblicua complica preguntas sencillas:
- ¿esta persona está realmente en la mesa o delante de ella?
- ¿está entrando en la zona o solo cruzando el pasillo?
- ¿qué parte del suelo o plano útil corresponde a cada píxel?

La vista cenital intenta responder a estas preguntas en un espacio más fácil de razonar.

## Vista de pájaro

### Qué es
Es una transformación del plano observado para representarlo como si se viera desde arriba.

### Valor para RestaurIA
Permite que:
- zonas y mesas se definan con lógica espacial más limpia,
- la pertenencia a mesa sea más estable,
- los pasillos se interpreten mejor,
- y el dashboard técnico pueda mostrar un mapa operativo más claro.

### Aplicación práctica
Cuando el suelo o el plano útil se puede mapear con cuatro puntos fiables:
- se calcula la transformación,
- se rectifica el frame o el plano relevante,
- y se procesan zonas en ese espacio transformado.

## Homografía operativa

### Relación con este documento
La homografía ya se documentó como base matemática de rectificación.

Aquí se fija su valor de producto:
- no solo corrige la imagen,
- sino que puede generar una representación operativa del restaurante.

### Decisión
Si una cámara del piloto tiene perspectiva que dificulta claramente la lectura de mesas, la vista cenital pasa a ser una mejora prioritaria y justificable.

## Reproyección al vídeo

### Qué aporta
Una vez que existe geometría útil del espacio, es posible proyectar de vuelta sobre la imagen:
- etiquetas,
- estados,
- overlays,
- referencias de zona,
- y anotaciones alineadas con la escena real.

### Valor para RestaurIA
Esto permite que:
- la depuración visual sea más precisa,
- el vídeo anotado mantenga coherencia geométrica,
- y futuras etiquetas como ETA o estado queden bien ancladas a la mesa.

### Decisión
La reproyección debe registrarse como capacidad práctica de:
- vídeo anotado,
- laboratorio,
- y futuras interfaces técnicas.

No es necesario resolver proyección 3D compleja para aprovechar este valor.

## Estimación de pose

### Qué significa aquí
Dado un objeto o plano conocido, estimar posición y orientación relativa respecto a la cámara.

### Aplicación potencial
Podría ayudar a:
- recuperar configuración tras mover una cámara,
- alinear mejor mesas estándar,
- o automatizar parte del setup en fases posteriores.

### Decisión
No debe entrar en el MVP.
Debe quedar documentado como posible mejora de calibración y despliegue.

## Visión estéreo y profundidad

### Qué aportaría
Con dos cámaras bien calibradas, el sistema podría obtener profundidad más explícita.

### Valor potencial
Serviría para:
- distinguir mejor cuerpo humano de objetos colgados o apoyados,
- separar niveles de profundidad,
- reducir ciertos falsos positivos,
- y enriquecer la interpretación espacial.

### Decisión
Fuera del alcance del MVP y del piloto temprano.

Razón:
- complica hardware,
- calibración,
- sincronización,
- y procesamiento.

Debe quedar como línea de escalado si el producto lo exige y las métricas justifican el coste.

## Ajuste de líneas

### Qué aporta
El ajuste robusto de líneas puede ayudar a:
- detectar alineaciones de mesas,
- inferir pasillos,
- y asistir la configuración inicial del local.

### Valor práctico
Puede ser útil como herramienta de setup o validación geométrica, especialmente en locales con mobiliario ordenado en filas.

### Decisión
Técnica de apoyo útil para calibración y setup, no núcleo del MVP.

## Qué entra realmente en el proyecto

### Sí entra como valor práctico
- capacidad de vista cenital cuando la perspectiva lo exija,
- uso operativo de homografía,
- reproyección de overlays al vídeo,
- y mejor representación espacial del plano útil.

### No entra de inicio
- estéreo,
- reconstrucción 3D compleja,
- pose automática completa,
- ni infraestructura dual-cámara.

## Cómo encaja en la arquitectura

### Capa visual
Puede producir:
- frame rectificado,
- mapa cenital,
- coordenadas transformadas,
- y anclajes reproyectables.

### Capa de presentación
Puede usar:
- vídeo anotado con overlays alineados,
- plano cenital simplificado,
- y vistas técnicas de depuración o supervisión.

## Valor para el dashboard
La vista cenital no debe verse solo como herramienta técnica.

También puede convertirse en:
- una capa de supervisión,
- una vista secundaria de sala,
- o un soporte de explicación para el operador.

Eso sí:
- no sustituye automáticamente al vídeo real,
- sino que lo complementa cuando mejora comprensión.

## Recomendaciones de laboratorio
- probar si la vista cenital reduce errores de pertenencia a mesa,
- comparar comprensión con y sin rectificación,
- validar estabilidad visual de overlays reproyectados,
- y no introducir geometría más rica si el caso real no la necesita.

## Riesgos a vigilar
- mala selección de puntos de referencia,
- falsa sensación de precisión,
- deformación excesiva en homografías mal definidas,
- y complejidad de setup superior al beneficio real.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/03_datos_y_ml/16_calibracion_de_camara_y_precision_metrica.md`
- `docs/02_arquitectura/03_diagrama_textual_de_flujo.md`

## Conclusión
El valor principal de este capítulo para RestaurIA está en consolidar una idea muy importante:
- la cámara no solo captura una escena,
- puede alimentar un plano operativo más útil que la imagen original para ciertas decisiones.

La vista cenital y la reproyección bien usadas pueden convertir la percepción visual en una geometría mucho más accionable, sin obligar todavía al proyecto a entrar en complejidad 3D plena.
