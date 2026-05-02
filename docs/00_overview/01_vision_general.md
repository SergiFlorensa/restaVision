# Vision general del proyecto

## Nombre de trabajo
RestaurIA / restaVision

## Problema
En restaurantes con alta ocupacion, el director o responsable de sala toma decisiones criticas bajo presion:
- que grupo aceptar,
- cuanto tiempo de espera prometer,
- que mesa se liberara antes,
- cuando preparar o limpiar una mesa,
- que mesa esta desatendida,
- donde falta cobertura de personal,
- que decision puede empeorar la rotacion.

Normalmente estas decisiones se toman con intuicion, informacion parcial y mucho estres. El problema principal no es la falta de datos, sino convertir el estado de la sala en una accion clara en segundos.

## Propuesta de solucion
RestaurIA se configura como un **copiloto operativo de sala** local-first:
1. observa la sala con camaras y entradas manuales simples,
2. convierte observaciones en eventos operativos,
3. estima estados, tiempos y presion de servicio,
4. prioriza problemas,
5. recomienda la siguiente mejor accion,
6. explica el motivo,
7. registra si la recomendacion funciono.

La pregunta central del producto es:

```text
Y ahora que hago?
```

RestaurIA no debe limitarse a mostrar detecciones. Debe mostrar decisiones.

## Principios del sistema
- utilidad operativa por encima de sofisticacion tecnica,
- decision accionable por encima de dashboard saturado,
- latencia baja,
- explicabilidad,
- privacidad por diseno,
- modularidad,
- trazabilidad de decisiones.

## Resultado esperado
Un software que permita responder preguntas como:
- Que accion debe ejecutar ahora el encargado?
- Que espera realista se puede prometer a un grupo?
- Que mesa compatible se liberara antes?
- Que mesa esta finalizando, bloqueada o desatendida?
- Que decision conviene evitar porque reduce rotacion?
- Donde hay cuello de botella?

## Alcance del MVP
El MVP no intenta resolver todo. Se centra en:
- una camara o una fuente de observacion controlada,
- una zona o conjunto pequeno de mesas,
- cola manual asistida,
- sesiones y eventos persistidos,
- ETA baseline de liberacion,
- Promise Engine inicial para esperas,
- Top 3 acciones recomendadas,
- Modo Servicio Critico con ruido minimo.

## Alcance posterior
- multi-mesa,
- multi-camara,
- integracion con reservas, TPV/POS y KDS,
- recomendacion automatica de asignacion,
- analitica post-servicio,
- alertas discretas,
- aprendizaje por restaurante,
- dashboards multi-sede.
