CREATE USER restauria_app WITH PASSWORD 'cambiar_esta_password';
ALTER USER restauria_app SET client_encoding TO 'UTF8';
ALTER USER restauria_app SET timezone TO 'UTC';

CREATE DATABASE restauria_dev
    WITH
    OWNER = restauria_app
    ENCODING = 'UTF8'
    TEMPLATE = template0;

GRANT ALL PRIVILEGES ON DATABASE restauria_dev TO restauria_app;

