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
| `make metadata-verify` | Verifica inventario y operación del catálogo sin mutarlo. |
| `make demo-views` | Crea los espacios medallion (`Silver`, `Gold_*`) y las vistas Dremio aprobadas (ADR 0003). |
| `make metadata-dremio-sync` | Cataloga en OpenMetadata `Student_360` y las vistas medallion (bootstrap idempotente). |
| `make gateway` | Provisiona el usuario del gateway e inicia `metrics-gateway`. |
| `make metabase` | Inicia Metabase en `http://localhost:3030` (BI sobre Dremio). |
| `make db-shell` | Abre `psql` contra `moodle_db`. |
| `make shell SERVICE=langflow` | Abre una shell en el servicio indicado. |

## Arranque y verificación

```bash
make pull
make up
make check
```

La primera ejecución puede tardar varios minutos por la descarga de imágenes y las migraciones de OpenMetadata y Airflow. Un resultado correcto de `make ps` muestra MinIO y PostgreSQL como `healthy`; los trabajos `minio-create-buckets`, `postgres-init-openmetadata`, `postgres-init-airflow` y `openmetadata-migrate` terminan como `Exited (0)`. El servicio `ingestion` debe quedar en ejecución antes de desplegar pipelines desde OpenMetadata.

## Diagnóstico

```bash
make ps
make logs SERVICES=openmetadata-server
make logs SERVICES=langflow
make health
```

Si OpenMetadata no inicia, confirma que `openmetadata-migrate` terminó con código cero. Si el alta o despliegue de una ingesta muestra el error de Managed Airflow APIs, ejecuta `make health` y consulta `make logs SERVICES=ingestion`; la URL `http://localhost:8080/api/v1/openmetadata/health` debe responder correctamente. Si MinIO aparece como no saludable, revisa su endpoint con `make health` y sus registros con `make logs SERVICES=minio`.

## Capa federada Dremio (medallion) y BI

La capa federada sigue la arquitectura medallion del [ADR 0003](docs/adr/0003-dremio-medallion-audience-spaces.md): bronce = fuentes registradas; plata = espacio `Silver` (reglas de negocio); oro = espacios `Gold_Rectoria`, `Gold_Decanatos`, `Gold_VR_Financiera` (agregados de consumo). Metabase y el gateway sólo deben consultar los espacios `Gold_*`.

Mantenimiento típico de la capa federada, en este orden:

```bash
make demo-views            # recrea espacios y vistas en Dremio
make metadata-dremio-sync  # cataloga los cambios en OpenMetadata
make metadata-verify       # valida inventario, DAGs y lineage
```

`make demo-views` es idempotente: recrear una vista ya catalogada conserva owner y descripción en OpenMetadata; si una vista cambia de nombre o de espacio, elimina manualmente el activo obsoleto en OpenMetadata antes del sync.

## Gateway de métricas

El servicio `metrics-gateway` lleva el código embebido en la imagen (no monta volumen): después de editar `gateway/app.py` ejecuta `make gateway` para reconstruir y recrear el contenedor. Valida siempre `http://localhost:8092/api/v1/metrics/academic?sql=SELECT%201` → HTTP 400 y `/health` → ok.

## Metabase

`make metabase` inicia BI en `http://localhost:3030` (sólo localhost). En el primer acceso se crea la cuenta administradora local de desarrollo. Para conectar Dremio: **Admin → Databases → Add database → PostgreSQL**, con host `dremio`, puerto `31010` (wire protocol PostgreSQL de Dremio), base `Dremio` y el usuario de lectura `lab_viewer`. Restricción de gobierno: los dashboards deben construirse únicamente sobre datasets de los espacios `Gold_*`; `Silver` y las fuentes son capas internas de cálculo. En Dremio OSS esta restricción es convención documentada, no un control de acceso técnico; el control duro para consumidores externos sigue siendo el gateway (ADR 0002).

## Datos persistentes

`make down` preserva los volúmenes Docker. La eliminación de volúmenes borra bases de datos, objetos y metadatos; no se automatiza mediante Make para evitar pérdida accidental de datos.

## Límites de seguridad

Este Compose deshabilita la seguridad de OpenSearch y publica varios puertos de datos. Úsalo exclusivamente en una máquina o red de desarrollo controlada.
