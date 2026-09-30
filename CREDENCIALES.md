# Accesos del entorno Docker Compose

> Estas credenciales son exclusivas del entorno local de desarrollo. No se deben reutilizar ni exponer fuera de una red controlada.

| Servicio | URL o conexión | Usuario | Contraseña | Notas |
| --- | --- | --- | --- | --- |
| PostgreSQL (Moodle) | `postgresql://localhost:5432/moodle_db` | `postgres` | `PostgresPassword123!` | Base transaccional. |
| PostgreSQL (OpenMetadata) | `postgresql://localhost:5432/openmetadata_db` | `postgres` | `PostgresPassword123!` | Base de gobierno creada por el inicializador. |
| SQL Server | `localhost:1433` | `sa` | `MssqlPassword123!` | Edición Developer. |
| DbGate | http://localhost:3000 | No aplica | No aplica | Interfaz local; conexiones Moodle y ERP con `lab_viewer` (solo lectura). |
| MinIO — consola | http://localhost:9001 | `admin` | `MinioPassword123!` | La API S3 está en http://localhost:9000. Buckets: `university-lakehouse` y `openrag-docs`. |
| Dremio | http://localhost:9047 | `matias` | `matias123` | Administrador local; contiene los sources `Moodle_Postgres` y `ERP_MSSQL`. |
| Gateway de métricas | http://localhost:8092 | No aplica | No aplica | Punto de consumo local: sólo resúmenes rectorales aprobados; no expone SQL ni credenciales Dremio. |
| OpenSearch | http://localhost:9200 | No aplica | No aplica | El plugin de seguridad está deshabilitado para este entorno local. |
| Langflow | http://localhost:7860 | `admin` | `LangflowPassword123!` | Superusuario configurado por Compose. |
| OpenMetadata | http://localhost:8585 | `admin@open-metadata.org` | `admin` | Credenciales iniciales predeterminadas de OpenMetadata 1.3.1. |
| Airflow de ingestas | http://localhost:8080 | `admin` | `admin` | Ejecuta los pipelines desplegados desde OpenMetadata; disponible solo en localhost. |
| Metabase (BI) | http://localhost:3030 | `admin@datalab.local` | `MetabaseAdmin123!` | Administrador local de la capa BI; se conecta a Dremio por Flight SQL (32010). |
| Dremio (BI) | `dremio:32010` (Flight SQL) | `metabase_reader` | `MetabaseReader123!` | Usuario de solo consulta para Metabase; consumo limitado a los espacios `Gold_*`. |

## Servicios auxiliares

`minio-create-buckets`, `postgres-init-openmetadata`, `postgres-init-airflow` y `openmetadata-migrate` son trabajos de inicialización: se ejecutan y finalizan automáticamente; no tienen interfaz ni credenciales de acceso propias.

## Recomendación

Cambia las contraseñas de MinIO, Langflow, PostgreSQL, SQL Server, `lab_viewer`, Metabase y `metabase_reader` antes de compartir el entorno o publicar cualquiera de sus puertos.
