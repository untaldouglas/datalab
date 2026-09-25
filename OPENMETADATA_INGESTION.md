# Ingestas de OpenMetadata

## Hallazgo y causa

OpenMetadata Server no ejecuta conectores desde su interfaz. La acción **Add Metadata Ingestion** crea y despliega un DAG mediante Apache Airflow y las **OpenMetadata Managed Airflow APIs**.

Una instalación que solo contiene `openmetadata-server`, su base de datos y el motor de búsqueda puede mostrar el servicio de base de datos, pero no puede desplegar ni ejecutar ingestas. El síntoma es:

> Failed to find OpenMetadata - Managed Airflow APIs

En este entorno la causa fue la ausencia del servicio `ingestion` y de su endpoint interno. No se debía a la conexión PostgreSQL de Moodle ni a las credenciales `lab_viewer`.

## Diseño de esta implementación

El archivo `docker-compose.yml` incorpora:

- `ingestion`, usando `docker.getcollate.io/openmetadata/ingestion:1.3.1`.
- Airflow con `LocalExecutor` y las Managed Airflow APIs incluidas por la imagen oficial.
- La base `airflow_db`, creada de forma idempotente por `postgres-init-airflow`.
- Volúmenes persistentes para DAGs generados, configuración de DAGs y archivos temporales.
- El endpoint interno `http://ingestion:8080` configurado en OpenMetadata mediante `PIPELINE_SERVICE_CLIENT_ENDPOINT`.

Las imágenes del servidor OpenMetadata y de ingesta deben usar exactamente la misma versión. Actualmente ambas son `1.3.1`.

## Verificación posterior a una reimplementación

1. Inicia el stack con `make up`.
2. Espera a que `postgres-init-airflow` finalice correctamente y `ingestion` permanezca en ejecución.
3. Ejecuta `make health`. Además de los demás servicios, valida `http://localhost:8080/api/v1/openmetadata/health`.
4. En OpenMetadata, abre el servicio de base de datos y crea o despliega la ingesta. El estado debe pasar de `deployed: false` a desplegado y permitir ejecutar el DAG.
5. Revisa los registros si falla:

   ```bash
   make logs SERVICES=ingestion
   make logs SERVICES=openmetadata-server
   ```

## Límites y seguridad

Airflow se publica exclusivamente en `127.0.0.1:8080`. Sus credenciales son de desarrollo y están registradas en `CREDENCIALES.md`; deben sustituirse antes de compartir el entorno. Moodle sigue utilizando `lab_viewer`, limitado a lectura.

No cambies `SERVER_HOST_API_URL` por `localhost` mientras el ejecutor esté en Docker: desde el contenedor `ingestion`, `localhost` se refiere al propio contenedor y no al servidor OpenMetadata.

## Pipelines iniciales transaccionales

Cada fuente transaccional tiene una conexión de solo lectura con `lab_viewer`, un pipeline de metadatos habilitado y una primera ejecución manual que debe finalizar en `success` antes de depender de la programación diaria.

| Servicio | Pipeline | Esquema | Horario (`America/El_Salvador`) |
| --- | --- | --- | --- |
| `Moodle_Postgres` | `Moodle_Postgres_metadata` | `moodle` | 02:00 |
| `ERP_MSSQL` | `ERP_MSSQL_metadata` | `erp` | 02:05 |
| `SIS_MSSQL` | `SIS_MSSQL_metadata` | `sis` | 02:10 |
| `ERPNext_Postgres` | `ERPNext_Postgres_metadata` | `erp` | 02:15 |

Si un pipeline fue creado antes de añadir `ingestion`, aparecerá como `deployed: false`. No hay que recrear la conexión de la fuente: desde la pestaña **Ingestions** del servicio correspondiente, selecciona el pipeline, pulsa **Deploy** y después **Run**. La ingesta solo lee la fuente; el resultado se almacena en el catálogo de OpenMetadata.
