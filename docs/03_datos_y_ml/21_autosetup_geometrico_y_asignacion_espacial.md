# Auto-setup geométrico y asignación espacial

## Propósito
Definir técnicas avanzadas para:
- detectar automáticamente geometría útil del local,
- reducir parte de la configuración manual,
- y mejorar la asignación espacial de personas o grupos a mesas.

Este documento cubre:
- detección automática de mesas y líneas,
- mapas de influencia y Voronoi,
- ecualización de histograma como ayuda de robustez,
- y watershed para separar regiones activas muy próximas.

## Decisión técnica principal
Estas técnicas tienen valor claro para el proyecto, pero no deben desplazar el enfoque del MVP temprano:
- **setup manual simple primero**,
- **auto-setup y asignación espacial avanzada después**.

Regla:
- si una técnica reduce trabajo manual o falsos positivos de forma medible, merece entrar;
- si solo añade complejidad sin mejorar una decisión real, debe quedar como exploración.

## 1. Detección automática de mesas

### Hough para círculos
Puede ser útil si el local tiene:
- mesas redondas,
- platos de referencia,
- o geometría circular clara en la escena.

Valor:
- detectar centro y radio aproximados,
- proponer zonas iniciales,
- o acelerar calibración.

Limitaciones:
- sensible a perspectiva,
- sensible a oclusiones,
- y poco fiable si la mesa no se ve completa o está ocupada.

### LSD para líneas
El detector de segmentos de línea puede ser más útil que Hough clásica para:
- bordes de mesas rectangulares,
- alineaciones de pasillo,
- estructura del local,
- y apoyo a setup semiautomático.

Valor para RestaurIA:
- sugerir rectángulos o líneas guía,
- detectar alineaciones,
- y ayudar a reposicionar zonas si hay pequeños movimientos del mobiliario.

### Decisión
La detección automática de mesas debe considerarse:
- ayuda al setup,
- no sustituto completo de validación humana.

El sistema puede:
- proponer geometrías,
- pero una persona debe confirmarlas antes de consolidarlas.

## 2. Transformada de distancia y mapas de influencia

### Qué aportan
Permiten estimar para cada punto su cercanía al objeto o región más próxima.

### Valor para el proyecto
Esto es especialmente interesante para:
- asignar una persona de pie a una mesa cercana,
- crear zonas de influencia alrededor de mesas,
- gestionar grupos cerca de su mesa,
- y resolver ambigüedad espacial sin depender solo de rectángulos rígidos.

### Lectura operativa útil
La pregunta deja de ser solo:
- “¿está dentro del rectángulo?”
y pasa a ser también:
- “¿a qué mesa pertenece más probablemente este punto o blob?”

### Decisión
Los mapas de influencia merecen registrarse como una de las mejoras espaciales más prometedoras después del MVP temprano.

No son obligatorios para arrancar, pero sí muy valiosos para:
- mesas próximas,
- personas de pie,
- y zonas de espera o transición.

## 3. Ecualización de histograma

### Qué problema ataca
La exposición desigual y las variaciones de luz pueden degradar la señal de cámaras inalámbricas o cámaras económicas.

### Valor real
Puede mejorar:
- contraste,
- legibilidad de regiones oscuras,
- y estabilidad de algunos algoritmos posteriores.

### Riesgo
También puede:
- exagerar ruido,
- introducir artefactos,
- o alterar la apariencia de fondo de forma contraproducente.

### Decisión
Debe usarse como:
- herramienta por cámara conflictiva,
- opción de pipeline,
- no paso universal fijo.

## 4. Watershed como segmentación dirigida

### Qué resuelve
Cuando varias personas o regiones activas quedan fundidas en una sola mancha, watershed puede ayudar a separarlas.

### Valor para RestaurIA
Podría ser útil en:
- mesas grandes,
- grupos muy próximos,
- o escenas donde un blob único no basta.

### Limitaciones
Necesita:
- buenos marcadores,
- máscaras razonables,
- y una escena donde la separación realmente merezca el coste.

### Decisión
No entra como baseline del MVP.
Debe reservarse para:
- laboratorio,
- escenas especialmente difíciles,
- o futuras mejoras de separación persona↔persona.

## Estrategia recomendada por fases

### MVP temprano
- zonas definidas manualmente,
- validación humana,
- lógica espacial simple.

### MVP ampliado
- asistencia al setup con LSD o Hough,
- validación manual posterior,
- y primeras zonas de influencia.

### Fase intermedia
- mapas de influencia o Voronoi,
- asignación más rica persona↔mesa,
- watershed si la separación de blobs lo exige.

## Qué entra realmente en el proyecto

### Sí entra como línea prioritaria de evolución
- asistencia al setup con líneas y geometría,
- mapas de influencia para asignación espacial,
- y ecualización por cámara si mejora robustez.

### Queda como exploración
- auto-detección completa de mesas sin revisión humana,
- watershed como separador general,
- y cualquier automatización geométrica no validada en local real.

## Relación con otros documentos
Este documento complementa:
- `docs/03_datos_y_ml/11_transformaciones_geometricas_y_rectificacion.md`
- `docs/03_datos_y_ml/14_sustraccion_de_fondo_y_segmentacion_de_primer_plano.md`
- `docs/03_datos_y_ml/17_proyeccion_operativa_y_vista_cenital.md`
- `docs/04_software_y_devops/08_highgui_herramienta_de_calibracion.md`

## Conclusión
Estas técnicas son muy valiosas para hacer que RestaurIA evolucione desde un sistema calibrado manualmente hacia uno más autónomo y espacialmente más inteligente.

La prioridad correcta es:
- primero un setup manual fiable,
- luego ayuda automática,
- y solo después automatización geométrica más ambiciosa cuando las métricas y el entorno la justifiquen.
