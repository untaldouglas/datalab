# Operación local

## Automatización

El `Makefile` centraliza las operaciones comunes:

| Comando | Acción |
| --- | --- |
| `make help` | Lista objetivos y variables disponibles. |
| `make config` | Valida y resuelve la configuración de Docker Compose. |
| `make pull` | Descarga las imágenes definidas. |
| `make up` | Inicia el stack en segundo plano y elimina servicios huérfanos. |
| `make ps` | Muestra estado, puertos y healthchecks. |
| `make logs` | Sigue los registros de todos los servicios. |
| `make logs SERVICES=minio` | Sigue los registros del servicio indicado. |
| `make health` | Comprueba PostgreSQL y los endpoints HTTP publicados. |
| `make check` | Ejecuta validación de configuración y comprobaciones de salud. |
| `make restart` | Reinicia el stack conservando volúmenes. |
| `make down` | Detiene y elimina contenedores y red, conservando volúmenes. |
| `make db-shell` | Abre `psql` contra `moodle_db`. |
| `make shell SERVICE=langflow` | Abre una shell en el servicio indicado. |

## Arranque y verificación

```bash
make pull
make up
make check
```

La primera ejecución puede tardar varios minutos por la descarga de imágenes y las migraciones de OpenMetadata. Un resultado correcto de `make ps` muestra MinIO y PostgreSQL como `healthy`; los trabajos `minio-create-buckets`, `postgres-init-openmetadata` y `openmetadata-migrate` terminan como `Exited (0)`.

## Diagnóstico

```bash
make ps
make logs SERVICES=openmetadata-server
make logs SERVICES=langflow
make health
```

Si OpenMetadata no inicia, confirma que `openmetadata-migrate` terminó con código cero. Si MinIO aparece como no saludable, revisa su endpoint con `make health` y sus registros con `make logs SERVICES=minio`.

## Datos persistentes

`make down` preserva los volúmenes Docker. La eliminación de volúmenes borra bases de datos, objetos y metadatos; no se automatiza mediante Make para evitar pérdida accidental de datos.

## Límites de seguridad

Este Compose deshabilita la seguridad de OpenSearch y publica varios puertos de datos. Úsalo exclusivamente en una máquina o red de desarrollo controlada.
