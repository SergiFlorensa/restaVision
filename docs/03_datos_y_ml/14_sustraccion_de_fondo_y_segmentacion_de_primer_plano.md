# Sustracción de fondo y segmentación de primer plano

## Propósito
Definir cómo usar técnicas de segmentación para separar la actividad relevante del fondo visual en RestaurIA, especialmente en el problema central del MVP:
- saber si una mesa está vacía,
- alterada,
- u ocupada.

Este documento se centra en:
- sustracción de fondo,
- máscaras de primer plano,
- limpieza por componentes,
- y segmentación clásica útil para el laboratorio y el MVP.

## Decisión técnica principal
La sustracción de fondo debe considerarse una de las bases técnicas más prometedoras del MVP clásico de ocupación por mesa.

Eso sí:
- debe aplicarse por ROI o zona,
- debe combinarse con limpieza y filtrado,
- y no debe convertirse en la única fuente de verdad del sistema.

## Problema que resuelve
Si una cámara observa una mesa fija, una gran parte de la escena es estable:
- mesa,
- suelo,
- sillas,
- pared,
- decoración.

Lo que interesa detectar es la desviación relevante respecto a esa referencia:
- personas,
- movimiento corporal,
- objetos nuevos importantes,
- cambios de ocupación.

La sustracción de fondo permite precisamente eso:
- separar fondo esperado de intrusión o cambio útil.

## Lugar en la arquitectura
Esta capa pertenece a `services/vision/` y actúa después de:
- captura,
- rectificación opcional,
- extracción de ROI,
- y cierto preprocesado básico.

Flujo recomendado:

```text
ROI
  -> preprocesado
  -> modelo de fondo o referencia
  -> máscara de primer plano
  -> limpieza
  -> componentes / contornos
  -> observación de zona
```

## 1. Sustracción de fondo como baseline

### Idea general
El sistema aprende cómo se ve una ROI en condiciones normales de fondo y marca como primer plano los píxeles que se desvían de ese patrón.

### Por qué encaja bien en RestaurIA
Porque en el MVP trabajamos con:
- cámaras fijas,
- zonas relativamente estables,
- una o pocas mesas,
- y necesidad de una solución explicable y barata.

## 2. Fondo simple vs. fondo robusto

### Fondo simple
Ejemplo:
- una imagen de referencia de mesa vacía.

Ventajas:
- fácil de entender,
- fácil de implementar.

Limitaciones:
- sensible a cambios de luz,
- sensible a variaciones lentas,
- frágil en entornos reales.

### Fondo robusto / adaptativo
Uso:
- permitir que el modelo aprenda rangos razonables a lo largo del tiempo,
- no solo una instantánea fija.

### Decisión para el proyecto
El MVP debe contemplar ambos niveles:
- referencia vacía como baseline inicial,
- modelo adaptativo como mejora clásica si el entorno lo exige.

## 3. Modelo tipo codebook

### Qué aporta conceptualmente
Un modelo tipo codebook no memoriza un único valor por píxel, sino un conjunto tolerado o rango de variación compatible con el fondo.

### Por qué es valioso
Puede absorber mejor:
- pequeñas oscilaciones de iluminación,
- parpadeo,
- variaciones graduales,
- y cambios ambientales no relevantes.

### Decisión
Debe registrarse como una línea técnica valiosa para el MVP ampliado o para cámaras complicadas, pero no es obligatorio imponerlo desde el minuto uno si una referencia simple por ROI funciona en laboratorio.

### Cuándo merece la pena usarlo
El enfoque codebook tiene más sentido cuando:
- la cámara es fija pero el fondo no es perfectamente estático,
- hay cambios graduales de iluminación,
- existen oscilaciones repetidas de brillo,
- o el fondo contiene pequeñas variaciones frecuentes no relevantes.

### Qué problema mejora frente a una referencia vacía simple
Una referencia simple pregunta:
- “¿este píxel es parecido a una sola foto del fondo?”

Un codebook pregunta:
- “¿este píxel encaja en alguno de los estados normales que este fondo ha mostrado a lo largo del tiempo?”

Esa diferencia lo hace más robusto ante:
- parpadeos,
- reflejos variables,
- zonas cercanas a ventana,
- y pequeñas dinámicas del entorno.

## 3.1. Estructuras conceptuales del codebook

### `code_element`
Cada elemento representa una caja o rango aceptado de valores para un píxel.

Conceptualmente debería guardar:
- mínimo observado,
- máximo observado,
- límites de aprendizaje,
- tiempo desde la última actualización,
- y alguna medida de vigencia o caducidad.

### `code_book`
Cada píxel tiene asociado un pequeño conjunto de `code_element` que representa sus estados normales posibles.

En implementación moderna del proyecto, esto no obliga a copiar las estructuras C del libro literalmente, pero sí a conservar el mismo modelo lógico:
- varios estados de fondo posibles por píxel,
- actualización incremental,
- y limpieza de entradas caducas.

## 3.2. Fase de aprendizaje

### Objetivo
Aprender cómo se comporta una ROI o zona cuando pertenece al fondo.

### Flujo conceptual
Para cada frame de entrenamiento:
1. se toma el valor del píxel,
2. se compara contra sus entradas existentes,
3. si encaja, se actualiza la caja correspondiente,
4. si no encaja, se crea una nueva entrada.

### Recomendación para RestaurIA
La fase de aprendizaje debe ejecutarse:
- con la cámara ya estabilizada,
- idealmente con la mesa vacía o con actividad mínima,
- durante una ventana temporal suficiente,
- y registrando cuántos frames y condiciones participaron en el aprendizaje.

### Regla operativa
No aprender indefinidamente sin control.
Debe existir una fase explícita de:
- inicialización,
- consolidación,
- y congelación o actualización controlada del fondo.

## 3.3. Limpieza de entradas caducas

### Qué resuelve
Durante el aprendizaje pueden aparecer estados transitorios:
- una persona cruzando,
- un objeto temporal,
- una sombra puntual.

Si no se limpian, el modelo de fondo se contamina.

### Estrategia
Cada entrada del codebook debe llevar información temporal para poder decidir:
- si sigue siendo parte normal del fondo,
- o si fue un primer plano temporal que nunca debió consolidarse.

### Aplicación en RestaurIA
Esto es especialmente valioso en:
- mesas que no están vacías todo el tiempo durante el aprendizaje,
- locales donde la escena no puede controlarse perfectamente,
- y pilotos donde la cámara ya está colocada pero el entorno no se puede “vaciar” por completo.

## 3.4. Segmentación en tiempo real

### Qué hace el modelo
Una vez entrenado, el codebook compara cada píxel actual con sus estados permitidos.

Resultado:
- si encaja en alguna caja, se considera fondo,
- si no encaja, se considera primer plano.

### Valor para el proyecto
Esto puede producir una máscara de primer plano más robusta que una resta simple contra una única referencia, especialmente en cámaras difíciles.

### Regla práctica
Aunque el codebook opere a nivel de píxel, en RestaurIA siempre debe integrarse con:
- ROI por mesa,
- limpieza morfológica,
- componentes o contornos,
- y lógica temporal por zona.

## 3.5. Flujo recomendado de codebook en RestaurIA

```text
ROI
  -> preprocesado ligero
  -> actualización controlada del codebook
  -> comparación contra codebook
  -> máscara de primer plano
  -> apertura/cierre
  -> componentes conectados o contornos
  -> filtrado por área
  -> señales de ocupación
```

## 3.6. Posición del codebook en la estrategia del proyecto

### Baseline más simple
- referencia vacía por ROI,
- diferencia simple,
- umbralización,
- morfología,
- contornos.

### Baseline más robusto
- codebook por ROI o por frame,
- limpieza de entradas caducas,
- segmentación más estable,
- y mismas etapas posteriores de limpieza y medición.

### Decisión de adopción
El codebook debe entrar si demuestra:
- menor sensibilidad a cambios de luz,
- menos falsos positivos,
- y mejor estabilidad temporal que la referencia vacía simple.

## 3.7. Implementación moderna recomendada

### Qué no hacer
No conviene trasladar literalmente la implementación C del libro al núcleo del proyecto en Python si eso produce:
- código opaco,
- estructuras difíciles de mantener,
- o penalización de rendimiento por mala adaptación.

### Qué sí hacer
Conservar la lógica del algoritmo pero implementarla de forma mantenible, por ejemplo:
- módulo específico de `background_model`,
- estructuras bien encapsuladas,
- entrenamiento y limpieza explícitos,
- y separación entre aprendizaje, inferencia y depuración.

## 3.8. Requisitos de validación del codebook

Antes de adoptarlo en el sistema, debe medirse:
- tasa de falsos positivos con cambios de luz,
- estabilidad del fondo tras varias horas,
- sensibilidad a oclusiones temporales,
- tiempo de aprendizaje razonable,
- y coste computacional por ROI o por frame.

## 4. Máscara cruda de primer plano
La sustracción de fondo genera una máscara inicial que rara vez será usable tal cual.

Problemas típicos:
- puntos aislados,
- ruido fino,
- sombras,
- agujeros dentro de regiones útiles,
- regiones conectadas artificialmente.

Por eso, la máscara debe pasar por:
- limpieza morfológica,
- filtrado por tamaño,
- y análisis de componentes o contornos.

## 5. Componentes conectados

### Valor práctico
Los componentes conectados permiten agrupar píxeles vecinos activos en regiones significativas.

En RestaurIA esto sirve para:
- eliminar ruido pequeño,
- estimar masa activa real,
- separar blobs relevantes,
- y apoyar el conteo o la ocupación.

### Regla práctica
Después de la máscara:
- filtrar por área mínima,
- descartar residuos pequeños,
- quedarse con componentes razonables para persona o grupo.

## 6. Watershed

### Qué resuelve
Watershed es útil cuando varias regiones activas están unidas y se quiere separarlas.

### Aplicación potencial
Podría ayudar cuando:
- dos personas quedan fusionadas en una misma mancha,
- o un blob incluye varias partes conectadas de forma ambigua.

### Decisión
No debe formar parte del baseline inicial.

Debe considerarse una técnica de:
- laboratorio,
- análisis avanzado,
- o mejora posterior cuando la fusión de blobs sea un problema real medido.

## 7. Mean-shift

### Qué aporta
Agrupa píxeles por similitud de color y proximidad espacial.

### Valor en el proyecto
Puede servir como presegmentación o simplificación visual en escenas complicadas.

### Decisión
No conviene introducirlo en el MVP temprano salvo que una prueba concreta demuestre una ganancia clara.

Se considera:
- técnica exploratoria,
- no baseline obligatorio.

## 8. Delaunay y Voronoi

### Valor potencial
Estas técnicas tienen interés geométrico para analizar vecindad y distribución espacial de puntos.

### Aplicación posible
Podrían tener valor en fases posteriores para:
- flujos de movimiento,
- disposición relativa de personas,
- o análisis espacial más rico de sala.

### Decisión
Fuera del núcleo del MVP.

## Señales que esta capa puede producir
- porcentaje de primer plano por ROI,
- número de componentes relevantes,
- área del mayor componente,
- dispersión de componentes,
- estabilidad del primer plano en el tiempo,
- y score de alteración de fondo.

## Estrategia baseline recomendada

```text
ROI
  -> preprocesado ligero
  -> comparación con referencia o fondo adaptativo
  -> máscara de primer plano
  -> apertura/cierre
  -> componentes conectados o contornos
  -> filtrado por área
  -> señales de ocupación
```

## Relación con otros documentos
Esta capa se conecta especialmente con:
- `docs/03_datos_y_ml/10_preprocesado_y_limpieza_de_senal_visual.md`
- `docs/03_datos_y_ml/13_contornos_y_metricas_geometricas.md`
- `docs/03_datos_y_ml/12_histogramas_y_matching_visual.md`

## Qué entra en el MVP
- referencia de fondo o referencia vacía por ROI,
- máscara de primer plano,
- limpieza morfológica,
- componentes o contornos,
- filtrado por tamaño,
- y generación de señales de ocupación por zona.

## Qué se deja para después
- codebook complejo si no es necesario al inicio,
- watershed como separador avanzado,
- mean-shift como presegmentación,
- y geometrías relacionales tipo Delaunay/Voronoi.

## Riesgos a vigilar
- sombras convertidas en primer plano,
- objetos pequeños mal interpretados,
- fondo que envejece mal con cambios reales del entorno,
- blobs fusionados,
- y falsas ocupaciones por cambios de luz o reflejos.

## Recomendaciones de laboratorio
- grabar mesa vacía en varias condiciones,
- medir diferencia entre referencia simple y fondo adaptativo,
- comparar limpieza con y sin morfología,
- ajustar área mínima por mesa,
- y documentar exactamente qué tipos de fallo aparecen.

## Conclusión
La sustracción de fondo es probablemente la técnica clásica más útil para arrancar RestaurIA con una mesa fija y una cámara estable.

Su valor no está en prometer inteligencia total, sino en ofrecer una base muy clara para responder la primera pregunta del MVP:
- “¿esta mesa sigue siendo fondo o ya hay algo relevante ocupándola?”
