# Instalación gratuita y configuración local

## Objetivo
Dejar el proyecto listo para desarrollarse sin herramientas de pago ni dependencias innecesarias.

## Qué ya está preparado dentro del repositorio
- entorno Python con `requirements/`,
- script de setup local,
- ejemplo de variables en `.env.example`,
- API del MVP,
- tests automáticos,
- configuración de `pre-commit`.

## Programas que necesitas tener instalados

### Obligatorios ahora
- **Python 3.11 o 3.12**
- **Git**

### Obligatorios en la siguiente fase
- **PostgreSQL Community Server**

### Recomendados
- **VS Code** o editor equivalente
- **pgAdmin 4** si prefieres gestionar PostgreSQL con interfaz gráfica

### No hace falta instalar todavía
- Docker Desktop
- CVAT
- Label Studio
- Grafana
- OpenVINO

Esos componentes tienen sentido más adelante, no en la primera fase del MVP.

## Qué ya está instalado en este entorno
- Python
- pip
- Git
- dependencias Python del proyecto en `.venv`

## Qué sigue faltando en este equipo
- PostgreSQL no está instalado o no está disponible en `PATH`

## Orden recomendado de instalación

### Paso 1. Entorno Python del proyecto
Ya puede montarse con:

```powershell
.\infra\scripts\setup_local.ps1
```

Ese script:
- crea `.venv`,
- actualiza `pip`,
- instala dependencias gratuitas,
- instala hooks de `pre-commit`,
- ejecuta los tests.

### Paso 2. PostgreSQL
PostgreSQL hace falta en cuanto pasemos de la persistencia en memoria actual a persistencia real con SQLAlchemy.

Ahora mismo:
- el MVP ya funciona sin Postgres,
- pero la siguiente fase técnica seria sí debe usarlo.

## Qué instalar de PostgreSQL

Instala la edición comunitaria gratuita de PostgreSQL.

Durante la instalación:
- deja el puerto por defecto `5432`,
- instala también `psql`,
- `pgAdmin` es opcional pero útil,
- define una contraseña fuerte para el usuario administrador `postgres`.

## Qué configurar en PostgreSQL

### Configuración mínima recomendada
- base de datos: `restauria_dev`
- usuario de aplicación: `restauria_app`
- puerto: `5432`
- codificación: `UTF8`
- zona horaria: `UTC`

### Script SQL preparado
El repositorio ya incluye:

```text
infra/db/01_create_local_dev_database.sql
```

Ese script crea:
- el usuario `restauria_app`,
- la base `restauria_dev`,
- y deja los parámetros mínimos recomendados.

## Cuándo configurar PostgreSQL

### Ahora mismo
Puedes dejarlo instalado ya para no frenarte después.

### Justo antes de la persistencia real
Es el momento obligatorio.

Cuando empecemos:
- modelos ORM,
- tablas reales,
- sesiones persistidas,
- eventos persistidos,
- predicciones guardadas,

entonces Postgres deja de ser opcional.

## Cómo crear la base de datos

### Opción 1. Con `psql`
Después de instalar PostgreSQL:

```powershell
psql -U postgres -f infra\db\01_create_local_dev_database.sql
```

### Opción 2. Con pgAdmin
1. Conectarte al servidor local.
2. Crear el usuario `restauria_app`.
3. Crear la base `restauria_dev`.
4. Asignar esa base al usuario.

## Variables de entorno del proyecto

Duplica `.env.example` a `.env` y ajusta como mínimo:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=restauria_dev
POSTGRES_USER=restauria_app
POSTGRES_PASSWORD=tu_password_real
DATABASE_URL=postgresql+psycopg://restauria_app:tu_password_real@127.0.0.1:5432/restauria_dev
ENABLE_POSTGRES=true
```

## Cómo arrancar la API local

```powershell
.\infra\scripts\run_api.ps1
```

O directamente:

```powershell
.\.venv\Scripts\uvicorn apps.api.main:app --reload
```

## Qué recomiendo como criterio profesional

### Imprescindible
- Python
- Git
- `.venv`
- tests
- `pre-commit`
- PostgreSQL instalado antes de la capa de persistencia

### Opcional pero útil
- pgAdmin
- VS Code

### Evitar por ahora
- contenedores,
- herramientas de anotación,
- observabilidad avanzada,
- servicios cloud.

## Siguiente paso técnico recomendado
El siguiente bloque serio del proyecto es sustituir la persistencia en memoria por persistencia real con SQLAlchemy y PostgreSQL.
