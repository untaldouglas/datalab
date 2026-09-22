# Accesos del entorno Docker Compose

> Estas credenciales son exclusivas del entorno local de desarrollo. No se deben reutilizar ni exponer fuera de una red controlada.

| Servicio | URL o conexión | Usuario | Contraseña | Notas |
| --- | --- | --- | --- | --- |
| PostgreSQL (Moodle) | `postgresql://localhost:5432/moodle_db` | `postgres` | `PostgresPassword123!` | Base transaccional. |
| PostgreSQL (OpenMetadata) | `postgresql://localhost:5432/openmetadata_db` | `postgres` | `PostgresPassword123!` | Base de gobierno creada por el inicializador. |
| SQL Server | `localhost:1433` | `sa` | `MssqlPassword123!` | Edición Developer. |
| MinIO — consola | http://localhost:9001 | `admin` | `MinioPassword123!` | La API S3 está en http://localhost:9000. Buckets: `university-lakehouse` y `openrag-docs`. |
| Dremio | http://localhost:9047 | Se define en el primer acceso | Se define en el primer acceso | El asistente inicial crea la cuenta administradora. |
| OpenSearch | http://localhost:9200 | No aplica | No aplica | El plugin de seguridad está deshabilitado para este entorno local. |
| Langflow | http://localhost:7860 | `admin` | `LangflowPassword123!` | Superusuario configurado por Compose. |
| OpenMetadata | http://localhost:8585 | `admin@open-metadata.org` | `admin` | Credenciales iniciales predeterminadas de OpenMetadata 1.3.1. |

## Servicios auxiliares

`minio-create-buckets`, `postgres-init-openmetadata` y `openmetadata-migrate` son trabajos de inicialización: se ejecutan y finalizan automáticamente; no tienen interfaz ni credenciales de acceso propias.

## Recomendación

Cambia las contraseñas de MinIO, Langflow, PostgreSQL y SQL Server antes de compartir el entorno o publicar cualquiera de sus puertos.
