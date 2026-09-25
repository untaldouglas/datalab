# Integrar Dremio mediante `CustomDatabase` y sincronización propia

**Estado: aceptada.** OpenMetadata 1.3.1 no distribuye un conector Dremio; por ello se decidió catalogarlo como `CustomDatabase` y sincronizar la vista federada `University_Lab.Student_360` mediante la API REST de Dremio y dos DAGs de Airflow. La alternativa de declararlo como PostgreSQL o Trino se rechazó porque esos protocolos y conectores no representan la API ni las capacidades reales de Dremio.

## Alternativas consideradas

- Actualizar toda la plataforma OpenMetadata para buscar un conector posterior: implica migrar servidor, Airflow, esquema y las integraciones ya verificadas, sin garantía de que la versión objetivo ofrezca lineage y usage para Dremio.
- Declarar Dremio como PostgreSQL o Trino: se descartó por ser técnicamente incorrecto y producir fallos o metadatos engañosos.
- Carga manual sin automatización: se descartó porque perdería cambios de la vista y no mantendría lineage ni usage.

## Consecuencias

La integración es explícita y reproducible, conserva el SQL de la VDS y mantiene lineage y usage, pero está limitada al contrato aprobado de `Student_360` y sus cuatro fuentes. Una nueva VDS o un cambio de dependencias requiere ampliar el contrato y sus pruebas; no se infiere lineage arbitrario. En producción, el JWT de `ingestion-bot` debe estar en un secreto de Airflow de mínimo privilegio; el acceso local a PostgreSQL existe sólo para el entorno de desarrollo.
