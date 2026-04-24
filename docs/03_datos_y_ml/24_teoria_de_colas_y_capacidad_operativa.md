# Teoría de colas y capacidad operativa

## Propósito
Definir cómo puede usar RestaurIA la teoría de colas para estimar:
- saturación del local,
- probabilidad de bloqueo o pérdida de grupos,
- presión de demanda por zona o servicio,
- y disponibilidad esperada de mesas.

Este documento no sustituye al ETA de una mesa concreta.
Su papel es complementario:
- `ETA` responde cuánto falta para liberar una mesa concreta,
- `teoría de colas` responde cómo de tensionado está el sistema en conjunto.

## Decisión técnica principal
La teoría de colas sí tiene encaje real en RestaurIA, pero como capa analítica de capacidad y no como verdad universal del producto.

Regla de proyecto:
- usar modelos de colas cuando sus supuestos encajen razonablemente con la operación real,
- no forzar una fórmula elegante sobre un restaurante cuya dinámica no cumple esas hipótesis.

## 1. Los tres pilares del modelo

### Proceso de entrada
Describe cómo llegan los grupos al sistema.

En RestaurIA esto se traduce en señales como:
- instante de llegada detectado,
- intervalo entre llegadas,
- tamaño del grupo,
- franja horaria,
- día de la semana,
- canal de entrada si existe esa información.

### Mecanismo de servicio
Describe cuántos servidores hay y cuánto dura el servicio.

En este proyecto:
- el servidor puede modelarse como `mesa`, `mesa utilizable` o `capacidad efectiva por zona`,
- y el tiempo de servicio es la duración observada de la sesión hasta liberación.

Variables útiles:
- número de mesas activas,
- duración media de sesión,
- percentiles de duración,
- tiempo medio de limpieza y reactivación.

### Disciplina de cola
Describe qué ocurre cuando no hay capacidad.

Casos posibles:
- el grupo espera,
- el grupo abandona,
- el host reorganiza mesas,
- o entra en lista de espera.

Este punto es crítico porque determina qué familia de modelos tiene sentido usar.

### Dos regímenes que conviene distinguir

#### BCC: Blocked Customers Cleared
Interpretación:
- si el sistema está lleno, el grupo no entra y se pierde.

Esto encaja con:
- locales sin espera real,
- picos donde el cliente decide irse,
- o zonas concretas donde no se mantiene cola operativa.

#### BCD: Blocked Customers Delayed
Interpretación:
- si el sistema está lleno, el grupo espera hasta que haya mesa.

Esto encaja con:
- host con lista de espera,
- recepción estructurada,
- o locales donde la espera forma parte normal de la operación.

### Decisión metodológica
RestaurIA debe poder documentar cuál de estos regímenes se aproxima mejor a cada local o zona.

No tiene sentido aplicar:
- Erlang B como si hubiera pérdida,
si en realidad hay cola,
ni aplicar:
- Erlang C como si hubiera cola estable,
si en realidad la mayoría de grupos se van.

## 2. Qué significa la carga ofrecida

### Definición
La carga ofrecida se puede expresar como:

```text
a = λ * τ
```

Donde:
- `λ` es la tasa de llegadas,
- `τ` es el tiempo medio de servicio,
- `a` se expresa en `erlangs`.

### Valor para RestaurIA
La carga ofrecida sirve para medir cuánta presión global recibe el sistema.

Interpretación operativa:
- si `a` crece pero la capacidad efectiva se mantiene, aumenta la tensión del servicio,
- si `a` se acerca o supera la capacidad útil, sube el riesgo de rechazo, espera o promesa irreal.

### Uso recomendado
Usar `a` como señal de:
- saturación inminente,
- comparación entre franjas,
- y variable de entrada para analítica de capacidad.

No usarla sola como reemplazo de:
- la ocupación real observada,
- el ETA por mesa,
- ni la decisión operativa instantánea.

## 3. Qué puede estimar el sistema

Con una capa de colas bien planteada, RestaurIA podría estimar:
- probabilidad de encontrar mesa libre,
- probabilidad de sistema saturado,
- tasa esperada de grupos perdidos,
- presión esperada en los próximos minutos,
- y sensibilidad ante cambios de capacidad.

Esto es especialmente útil para:
- host o recepción,
- supervisor de sala,
- análisis por turno,
- y simulación de escenarios.

## 3.1. Variables aleatorias y salidas probabilísticas

### Qué significa aquí
En esta capa, magnitudes como:
- número de grupos en sistema,
- tiempo de espera,
- tiempo hasta disponibilidad,
- o número de mesas ocupadas,
no deben entenderse solo como valores puntuales.

También pueden modelarse como variables aleatorias.

### Consecuencia para el producto
El sistema debería poder producir no solo:
- un valor esperado,
sino también salidas como:
- probabilidad de esperar más de `x` minutos,
- probabilidad de bloqueo,
- varianza de una estimación,
- percentiles esperados,
- o rango probable de disponibilidad.

### Métricas útiles
Cuando esta capa esté madura, interesa registrar:
- esperanza,
- varianza,
- percentiles,
- y estabilidad temporal de la estimación.

Esto es especialmente útil para no presentar:
- una promesa falsa de exactitud,
- ni un único número como si fuera certeza operativa.

## 3.2. Procesos de nacimiento y muerte

### Qué aportan
Los procesos de nacimiento y muerte ofrecen un marco natural para pensar:
- llegadas como `nacimientos`,
- salidas o liberaciones como `muertes`,
- y evolución del sistema como transición entre estados discretos.

### Valor para RestaurIA
Esto ayuda a formalizar:
- cambios en número de mesas ocupadas,
- equilibrio entre entrada y salida,
- y probabilidad de encontrarse en un estado operativo dado.

### Uso correcto
Debe verse como:
- marco matemático útil,
- base para analítica agregada,
- y herramienta de simulación o estimación.

No conviene convertirlo en:
- motor rígido del producto,
- ni asumir que cada local sigue exactamente un proceso markoviano ideal.

## 3.3. Estado estacionario

### Qué aporta
El estado estacionario sirve para describir el comportamiento de largo plazo de una franja o servicio cuando el sistema ya no depende mucho de la condición inicial.

### Valor para el proyecto
Esto encaja muy bien con:
- dashboards por franja,
- análisis por turno,
- comparación entre días,
- y KPIs estructurales de capacidad.

### Límite importante
No debe confundirse:
- estado estacionario analítico,
con
- predicción minuto a minuto durante un servicio real.

En restauración, la operación puede cambiar mucho entre:
- apertura,
- pico de servicio,
- sobremesa,
- cierre.

Por tanto, muchas veces conviene modelar por tramos y no asumir estacionariedad global durante todo el día.

## 4. Erlang B: cuándo sí encaja

### Qué modela
La fórmula de Erlang B es útil para sistemas con:
- capacidad finita,
- sin cola efectiva,
- y donde los clientes bloqueados se pierden o se van.

Aplicación conceptual:
- si todas las mesas están ocupadas y el grupo no espera, el sistema actúa como un sistema de pérdida.

### Qué puede aportar
Permite estimar:
- probabilidad de bloqueo,
- porcentaje esperado de grupos no atendidos,
- y presión relativa frente al número de mesas disponibles.

### Dónde encaja bien
Encaja mejor en:
- locales pequeños sin lista de espera real,
- terrazas o zonas donde el grupo decide irse si no entra,
- o análisis de capacidad teórica por franja.

### Dónde no encaja bien sin adaptación
No encaja bien, por sí sola, cuando hay:
- lista de espera,
- reservas fuertes,
- reasignación dinámica de mesas,
- mezcla compleja de tamaños de grupo,
- o tiempos de limpieza que crean un estado intermedio relevante.

### Decisión
Erlang B sí debe quedar documentado como herramienta analítica de capacidad.

Pero no debe convertirse en:
- el motor único de predicción,
- ni en la fórmula oficial del producto para cualquier restaurante.

### Nota importante sobre robustez
Una de sus ventajas teóricas es que la probabilidad de bloqueo depende sobre todo de:
- capacidad,
- carga ofrecida,
y no exige modelar cada detalle fino del tiempo de servicio para esta capa agregada.

Eso la hace atractiva para analítica temprana, siempre que el régimen `BCC` sea razonable.

## 4.1. Erlang C: cuándo merece entrar

### Qué modela
La fórmula de Erlang C es útil para sistemas con:
- capacidad de servicio finita,
- cola o espera estructurada,
- y grupos que no se pierden inmediatamente al llegar lleno.

### Qué puede aportar
Permite estimar:
- probabilidad de que un grupo tenga que esperar,
- presión esperada de la cola,
- y riesgo de que la espera se vuelva operativamente problemática.

### Condición de estabilidad
Para que este tipo de modelo tenga sentido estable, la carga ofrecida debe quedar por debajo de la capacidad efectiva.

Interpretación práctica:
- si la presión de entrada supera sistemáticamente la capacidad útil, la cola crecerá sin control o el supuesto del modelo dejará de parecerse a la realidad.

### Dónde encaja bien
Encaja mejor en:
- restaurantes con host y lista de espera real,
- operaciones donde la espera es habitual,
- y análisis por franja de congestión de acceso.

### Dónde no encaja bien sin adaptación
No encaja bien cuando:
- la espera es muy irregular,
- muchos grupos abandonan antes de sentarse,
- hay reservas que alteran de forma fuerte el flujo,
- o la asignación de mesas depende de reglas complejas de composición.

### Decisión
Erlang C debe quedar documentado como opción analítica para locales con espera estructurada.

No debe activarse por defecto si el sistema real no registra bien:
- llegada,
- inicio de espera,
- abandono,
- y sentado desde cola.

## 4.2. Carga transportada y ocupación

### Carga transportada
La carga transportada representa la carga realmente servida por el sistema.

En términos operativos puede leerse como:
- ocupación media efectiva,
- o número medio de mesas realmente ocupadas.

### Ocupación
La ocupación puede expresarse como:

```text
ρ = a' / s
```

Donde:
- `a'` es la carga transportada,
- `s` es la capacidad activa.

### Valor para el dashboard
Estas métricas son muy útiles para mostrar:
- nivel de utilización de la sala,
- margen operativo restante,
- diferencia entre demanda ofrecida y demanda realmente absorbida,
- y comparación entre zonas.

### Decisión
`ρ` sí merece quedar como KPI operativo visible en cuadros de mando internos.

## 4.3. Engset: caso de población finita

### Qué modela
El modelo de Engset tiene sentido cuando el conjunto de clientes potenciales es finito y relativamente cerrado.

### Dónde podría encajar
Ejemplos plausibles:
- comedor de empresa,
- club privado,
- residencia,
- hospital,
- o servicio interno con población conocida.

### Qué implica
En estos casos:
- la llegada no se parece tanto a una Poisson abierta,
- y la presión de entrada depende de cuántos potenciales clientes siguen fuera del sistema.

### Decisión
Engset queda documentado como caso especial de nicho.

No entra en el MVP general de restauración abierta, pero sí puede ser útil si el proyecto evoluciona a entornos cerrados o semiprivados.

## 5. Importancia de los supuestos

### Supuestos mínimos que conviene revisar
Antes de aplicar un modelo de colas hay que revisar:
- si las llegadas son aproximadamente estacionarias por franja,
- si la unidad de servicio se aproxima bien por mesa,
- si la pérdida al llegar lleno es real o no,
- y si el comportamiento cambia por zona, turno o tipo de servicio.

También conviene revisar:
- si una aproximación de Poisson para llegadas es razonable por tramo,
- si los tiempos de servicio tienen forma compatible con el modelo elegido,
- y si la cola real del restaurante se parece o no al supuesto analítico.

### Consecuencia práctica
El modelo correcto puede variar:
- `sin espera real` -> modelo tipo pérdida,
- `con espera estructurada` -> modelo con cola,
- `con reservas fuertes` -> modelo híbrido o simulación,
- `con grupos heterogéneos` -> segmentación por tamaños o capacidad efectiva.

## 5.1. Poisson, exponencial y Erlang: qué papel tienen

### Llegadas
La distribución de Poisson puede ser una aproximación razonable para:
- conteo de llegadas por intervalo,
- especialmente si se trabaja por franjas relativamente homogéneas.

No debe asumirse sin validación en:
- eventos especiales,
- locales con reservas dominantes,
- o servicios muy pautados.

### Tiempos de servicio
La distribución exponencial es matemáticamente cómoda, pero no debe imponerse por defecto a la duración de una mesa real.

Motivo:
- en un restaurante, el tiempo restante suele depender bastante de cuánto lleva ya ocupada la mesa,
- del momento del servicio,
- del tamaño del grupo,
- y del estado operativo observado.

### Conclusión práctica
La propiedad de falta de memoria es útil como referencia teórica en colas simples.

Pero en RestaurIA no debe convertirse en hipótesis base del ETA por mesa.

### Procesos por fases
Las distribuciones tipo Erlang o modelos por fases sí son conceptualmente interesantes cuando el servicio tiene etapas claras, por ejemplo:
- llegada y acomodación,
- consumo principal,
- postre o sobremesa,
- cuenta,
- salida.

Esto encaja mejor con la visión de producto que una exponencial pura, aunque requiere una semántica de estados bien definida.

## 6. Cómo encaja con la arquitectura de RestaurIA

### Capa de observación
Debe registrar:
- llegada detectada,
- ocupación de mesa,
- liberación,
- tiempo de limpieza,
- reentrada en disponibilidad,
- y, si existe, abandono sin servicio o espera iniciada.

### Capa de eventos
Debe poder emitir eventos como:
- `grupo_llega`,
- `grupo_espera`,
- `grupo_abandona`,
- `grupo_bloqueado_por_capacidad`,
- `grupo_sentado_desde_espera`,
- `mesa_se_libera`,
- `mesa_vuelve_a_disponible`.

### Capa analítica
Con esos eventos se calculan:
- `λ`,
- `τ`,
- capacidad efectiva,
- carga ofrecida,
- y scores de saturación o bloqueo.

Cuando el sistema madure, también puede calcular:
- distribuciones empíricas por franja,
- percentiles de espera,
- y probabilidades de superar umbrales relevantes.

## 7. Relación con ETA

### Diferencia esencial
El ETA responde:
- cuánto queda para una mesa concreta.

La teoría de colas responde:
- cómo se comporta el sistema agregado.

### Uso conjunto correcto
La mejor estrategia no es elegir una sola capa, sino combinarlas:
- ETA por mesa para decisiones finas,
- teoría de colas para visión agregada,
- y reglas de negocio para promesa al cliente.

Ejemplo:
- varias mesas con ETA aceptable,
- pero carga ofrecida muy alta y llegadas acelerándose,
- implica riesgo operativo aunque cada mesa aislada parezca controlada.

### Corrección metodológica importante
No conviene usar la propiedad de falta de memoria de la exponencial para justificar que el tiempo restante de una mesa no depende de su pasado.

En el producto real, para ETA sí importan señales como:
- tiempo transcurrido,
- fase de servicio,
- tamaño de grupo,
- actividad reciente,
- y contexto del turno.

La parte `memoryless` puede servir para teoría analítica simple, no como fundamento del predictor de liberación.

## 8. Qué entra en el MVP

### Sí entra de forma razonable
- cálculo de tasa de llegadas por franja,
- duración media y percentiles de sesión,
- carga ofrecida como métrica analítica,
- carga transportada y ocupación (`ρ`),
- score simple de saturación por zona o local.

### Puede entrar como analítica opcional temprana
- estimación experimental de bloqueo tipo Erlang B,
- o probabilidad de espera tipo Erlang C si existe lista de espera fiable,
- siempre marcada como aproximación y validada con datos reales.

### Se deja para después
- modelos de cola más complejos con espera explícita,
- simulación detallada,
- mezcla avanzada por tamaño de grupo,
- y promesas automáticas al cliente basadas solo en teoría de colas.

## 9. Recomendación de implementación

### Paso 1
Persistir bien estos eventos:
- llegada,
- ocupación,
- liberación,
- vuelta a disponible,
- abandono si puede medirse.

### Paso 2
Calcular por franja:
- `λ`,
- `τ`,
- ocupación media,
- rotación,
- carga ofrecida.

### Paso 3
Construir un primer dashboard analítico con:
- `carga actual`,
- `capacidad activa`,
- `ocupación efectiva`,
- `riesgo de saturación`,
- `probabilidad histórica de bloqueo por franja`,
- y `probabilidad histórica de espera` si aplica.

### Paso 4
Solo después comparar:
- baseline histórico,
- modelo sencillo de colas,
- y modelos predictivos más ricos.

## Relación con otros documentos
Este documento complementa:
- `docs/01_producto_y_negocio/02_kpis_y_metricas_de_negocio.md`
- `docs/03_datos_y_ml/01_fuentes_de_datos_y_eventos.md`
- `docs/03_datos_y_ml/18_ml_clasico_y_modelado_predictivo.md`
- `docs/03_datos_y_ml/19_random_forest_para_eta_de_liberacion.md`

## Conclusión
La teoría de colas aporta una capa muy valiosa para RestaurIA porque permite pensar el restaurante como sistema de capacidad, no solo como conjunto de mesas aisladas.

Su uso correcto es:
- analítico,
- explícito en sus supuestos,
- combinado con observación real,
- y subordinado a la operación concreta del local.
