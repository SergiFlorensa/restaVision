# Dateparser aplicado a reservas por voz

Fuente analizada:

```text
C:\Users\SERGI\Desktop\visionRestaIA Libros\dateparser-readthedocs-io-en-v1.3.0.pdf
```

## Por que aporta valor

En un agente telefonico de reservas, el cliente no habla como un formulario. Dice cosas como:

```text
manana a las nueve y media
este viernes a las 21
pasado manana a las 22:00
```

Antes, el agente solo trabajaba bien con horas simples. La mejora consiste en normalizar esas expresiones a una fecha/hora operativa que el motor de disponibilidad pueda usar.

## Contenido util extraido

Del documento de `dateparser`, las partes utiles para RestaurIA son:

- parseo de fechas relativas,
- `RELATIVE_BASE` para interpretar "manana" desde el momento real de llamada,
- `PREFER_DATES_FROM = future` para reservas,
- `DATE_ORDER = DMY` para contexto espanol,
- `TIMEZONE = Europe/Madrid`,
- `RETURN_AS_TIMEZONE_AWARE` para evitar ambiguedades,
- `DEFAULT_LANGUAGES = ["es"]` para llamadas en espanol,
- fallback a parser manual si la dependencia no esta instalada.

## Implementacion aplicada

Nuevo modulo:

```text
services/voice/time_parser.py
```

Capacidades:

- normaliza texto en espanol,
- entiende horas numericas: `21:30`, `21.30`, `21h30`,
- entiende `a las 21`,
- entiende expresiones relativas: `hoy`, `manana`, `pasado manana`,
- entiende dias de la semana: `viernes`, `sabado`, etc.,
- entiende horas frecuentes en texto: `a las nueve y media`, `a las ocho y cuarto`,
- usa `dateparser` si esta disponible,
- conserva fallback propio si no esta instalado.
- guarda fechas parciales si el cliente dice solo `viernes` o `manana`,
- combina la fecha parcial con una hora posterior en otro turno.

El agente de voz ahora guarda:

```text
requested_date_text: "08/05/2026"
requested_date: date
date_parser: manual_spanish | dateparser
requested_time_text: "03/05/2026 21:30"
requested_at: datetime timezone-aware
time_parser: manual_spanish | dateparser
```

## Fechas incompletas

El documento de `dateparser` advierte sobre el tratamiento de fechas incompletas mediante opciones como `STRICT_PARSING` y `REQUIRE_PARTS`. En RestaurIA esto se traduce a una regla de producto:

```text
"el viernes" no es suficiente para crear una reserva.
```

Flujo correcto:

```text
Cliente: Queria reservar mesa para 3 el viernes.
Agente: A que hora le gustaria la reserva?
Cliente: A las nueve y media.
Agente: Reserva confirmada para 3 personas el 08/05/2026 a las 21:30.
```

Esto evita que el sistema convierta una fecha sin hora en una reserva erronea a medianoche.

## Decision de dependencia

`dateparser==1.3.0` queda declarado en:

```text
requirements/audio.txt
```

La dependencia se considera alineada con el uso local/open source del proyecto. Aun asi, el backend no queda bloqueado si no esta instalada: el parser manual cubre los casos mas frecuentes para el MVP.

## Siguiente mejora posible

Con la fecha/hora normalizada, el siguiente salto natural es un motor de politicas de reserva:

- no reservar si queda poco para cierre de cocina,
- bloquear automaticamente mesas por reserva proxima,
- endurecer promesas en modo `critical`,
- proponer hora alternativa si no hay sitio a la hora solicitada.
