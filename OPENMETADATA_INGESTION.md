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

## Perfilado y calidad de datos

El catálogo transaccional se opera en tres etapas diarias y todas se ejecutan en la zona horaria `America/El_Salvador`:

| Capacidad | Cobertura | Pipelines | Horario |
| --- | --- | --- | --- |
| Ingesta de metadatos | 4 servicios, 18 tablas | Uno por servicio | 02:00–02:15, escalonado cada 5 minutos |
| Profiler | 4 servicios, 18 tablas | `*_profiler`, uno por servicio | 03:00–03:15, escalonado cada 5 minutos |
| Data Quality | 18 tablas | `*_dq`, uno por tabla | 04:00 |

Los cuatro pipelines de perfilado son `Moodle_Postgres_profiler`, `ERP_MSSQL_profiler`, `SIS_MSSQL_profiler` y `ERPNext_Postgres_profiler`. Calculan métricas y no generan datos de muestra (`generateSampleData: false`); esta última decisión evita exponer registros académicos o financieros en el catálogo.

Cada una de las 18 tablas tiene un Test Suite ejecutable y el control inicial `row_count_positive`. El control usa la definición `tableRowCountToBeBetween` con `minValue: 1`: detecta una fuente o carga inesperadamente vacía. No constituye una regla de negocio completa; antes de usar alertas operativas se deben añadir umbrales, unicidad, completitud y reglas de dominio acordadas con el responsable del activo.

La primera ejecución manual de los 4 profiler y de los 18 pipelines de Data Quality finalizó en `success`. Para validar una reimplementación desde la interfaz: abre una tabla, confirma el owner y la descripción, entra en **Profiler & Data Quality**, verifica `row_count_positive`, y abre el pipeline `*_dq` correspondiente en **Ingestions** para consultar su última ejecución.

## Responsabilidad y descripciones

Se completó la documentación de los activos transaccionales actualmente catalogados:

| Tipo de artefacto | Total | Owner | Descripción |
| --- | ---: | --- | --- |
| Bases de datos | 4 | `admin` | Sí |
| Esquemas | 4 | `admin` | Sí |
| Tablas | 18 | `admin` | Sí |
| Atributos/columnas | 111 | Responsabilidad de gobierno: owner de la tabla | Sí |

`admin` es el owner operativo temporal porque es la única cuenta administradora disponible en este entorno. En producción debe sustituirse por equipos o usuarios responsables de negocio (por ejemplo, Académica, Finanzas o TI) mediante la pestaña **Ownership** de cada base, esquema o tabla.

OpenMetadata 1.3 modela ownership nativo en entidades catalogables —como base, esquema y tabla—, no dentro de la definición individual de columna. Por ello, cada atributo se gobierna bajo el owner de su tabla; una excepción a esa responsabilidad debe documentarse como una regla de gobierno o modelarse con una propiedad personalizada aprobada, no simulando un owner nativo inexistente.
