# Anomalias operativas estadisticas

## Proposito
Este documento define como aplicar deteccion de anomalias al MVP sin sobredimensionar el sistema ni convertirlo en una herramienta acusatoria.

La idea util para RestaurIA es simple:
- una anomalia es una senal poco frecuente respecto al comportamiento historico,
- la senal debe servir para pedir revision humana,
- la alerta debe ser explicable con variables operativas,
- el sistema nunca debe afirmar automaticamente intenciones ni impagos.

## Alcance del MVP
La primera implementacion se limita a sesiones de mesa con duracion fuera del rango esperado.

Entrada:
- sesion activa,
- historico de sesiones cerradas de la misma mesa,
- hora actual de la observacion.

Salida:
- alerta operativa suave de tipo `long_session_attention`,
- severidad `warning`,
- evidencia numerica en `evidence_json`.

No se implementa en esta fase:
- deteccion automatica de impago,
- inferencia de intencion de clientes,
- modelos profundos de anomalias,
- dependencia de SciPy u otro paquete estadistico pesado.

## Criterio estadistico inicial
El detector calcula una distribucion historica de duraciones:
- numero de muestras,
- media,
- desviacion tipica poblacional.

Con suficientes muestras, una sesion activa se considera fuera de rango si:

```text
duracion_actual > media_historica + max(z_threshold * desviacion_tipica, margen_minimo)
```

El margen minimo evita alertas fragiles cuando el historico tiene muy poca variacion.

Valores iniciales:
- `min_samples = 5`,
- `z_threshold = 2.0`,
- `min_current_duration_seconds = 900`,
- `min_absolute_margin_seconds = 300`.

## Evidencia de alerta
Cada alerta incluye:
- duracion actual,
- umbral aplicado,
- numero de muestras historicas,
- media historica,
- desviacion tipica,
- exceso sobre el umbral,
- `z_score` cuando hay varianza suficiente,
- probabilidad de cola normal aproximada cuando procede.

La probabilidad de cola no debe interpretarse como verdad absoluta. Es una ayuda de lectura, no una decision automatica.

## Riesgos
Los tiempos de restaurante pueden tener colas pesadas, turnos no estacionarios y cambios por dia, clima, reservas o eventos.

Riesgos principales:
- falsos positivos en comidas largas normales,
- historico pequeno o sesgado,
- cambios de operativa entre franjas,
- asumir normalidad cuando la distribucion real no es normal.

Mitigaciones:
- minimo de muestras antes de alertar,
- margen absoluto minimo,
- lenguaje no acusatorio,
- decision final humana,
- futura separacion por franja horaria y tipo de servicio.

## Implementacion actual
Codigo:
- `services/alerts/anomaly.py`
- `GET /api/v1/alerts`

La alerta se genera desde el flujo de observaciones cuando hay una sesion activa y existe historico suficiente de sesiones cerradas. Para evitar ruido, se emite como maximo una alerta por sesion y tipo de alerta.

Persistencia:
- las alertas son operativas y en memoria en la primera version,
- la tabla `alerts` queda reservada para una fase posterior si se necesita auditoria persistente.

## Evolucion futura
Orden recomendado:
1. Persistir alertas si aportan valor en el dashboard.
2. Separar baselines por franja horaria y dia.
3. Medir precision, recall y falsos positivos de alertas.
4. Anadir confirmacion humana o estado `acknowledged`.
5. Evaluar Isolation Forest u otro modelo clasico solo si hay dataset suficiente.

No se debe avanzar a anomalias sensibles sin datos reales, validacion humana y revision legal.
