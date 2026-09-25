# Integración de Dremio con OpenMetadata

## Decisión y alcance

Dremio se integra como `Dremio_Federation`, un servicio `CustomDatabase`, porque la versión 1.3.1 de OpenMetadata usada por este stack no contiene un conector Dremio nativo. La integración no intenta emular otro motor: lee el catálogo y la definición SQL mediante la API REST de Dremio, y publica activos gobernables con la API de OpenMetadata.

El alcance actual es la VDS `University_Lab.Student_360`. Su contrato de lineage comprende `SIS_MSSQL.sis_db.sis.students`, `SIS_MSSQL.sis_db.sis.enrollments`, `Moodle_Postgres.moodle_db.moodle.users` y `ERPNext_Postgres.erpnext_db.erp.student_invoices`.

## Funcionalidades operativas

| Funcionalidad | Implementación | Frecuencia | Resultado |
| --- | --- | --- | --- |
| Bootstrap de catálogo | `dremio_openmetadata_sync.py bootstrap` | Al desplegar o bajo demanda | Crea de forma idempotente servicio, base, esquema y VDS con owner, SQL y columnas. |
| Lineage | `Dremio_Federation_lineage` | 04:30, `America/El_Salvador` | Valida el SQL de `Student_360` y publica sus cuatro relaciones upstream. |
| Usage | `Dremio_Federation_usage` | 04:45, `America/El_Salvador` | Consulta `sys.jobs_recent` y publica únicamente el delta de uso diario. |
| Descubrimiento | OpenSearch / Explore | Tras cada cambio de catálogo | La VDS y sus atributos aparecen en Explore y conservan enlaces al servicio. |

Los DAGs se definen en `dags/dremio_openmetadata.py`; el sincronizador está en `scripts/dremio_openmetadata_sync.py`. Ambos se montan de sólo lectura en el contenedor `ingestion`.

## Ventajas

- No altera Dremio ni duplica datos: consume sólo catálogo, SQL y historial de jobs.
- Evita catalogar Dremio bajo un conector incompatible.
- El bootstrap resuelve la VDS por ruta, no por UUID; por eso resiste una recreación de Dremio.
- Usage es idempotente para el día: no vuelve a sumar el historial al reintentar un DAG.
- La vista conserva owner, descripción, columnas y SQL, y sus fuentes permiten análisis de impacto.

## Limitaciones y riesgos

- No hay profiler ni Data Quality nativos sobre `CustomDatabase`; los controles continúan en las fuentes transaccionales.
- El lineage es un contrato controlado para `Student_360`, no un analizador SQL genérico para todas las VDS.
- Usage sólo cuenta ejecuciones REST que referencian explícitamente `"University_Lab"."Student_360"`; JDBC, ODBC, UI u otras VDS requieren ampliar el filtro y validar su semántica.
- En desarrollo el DAG obtiene el JWT del bot desde PostgreSQL. En producción debe usar un secreto de Airflow y una cuenta Dremio de sólo lectura con acceso a catálogo y `sys.jobs_recent`.

## Operación y reimplementación

1. Arranca el stack: `make up`.
2. Verifica Dremio y OpenMetadata: `make health`.
3. Ejecuta el bootstrap desde el contenedor de ingesta:

   ```bash
   docker exec poc-openmetadata-ingestion python /opt/airflow/dremio_sync/dremio_openmetadata_sync.py bootstrap
   ```

4. En Airflow habilita y ejecuta `Dremio_Federation_lineage` y `Dremio_Federation_usage`.
5. En OpenMetadata, abre `Dremio_Federation.Dremio.University_Lab.Student_360`; confirma cuatro fuentes en **Lineage** y el conteo diario en **Usage**.

Antes de añadir una VDS, define su owner, descripciones y fuentes aprobadas; después amplía `SOURCE_FQNS`, valida el SQL y añade una prueba de primera ejecución.
