# University Data Lab

Entorno local reproducible para experimentar con una plataforma de datos universitaria: fuentes transaccionales, almacenamiento de objetos, federación lakehouse, búsqueda, IA/RAG y gobierno de datos.

> Proyecto de demostración para desarrollo local. No está configurado para producción ni debe exponerse directamente a Internet.

## Componentes

| Capa | Servicio | Acceso local |
| --- | --- | --- |
| Fuente transaccional | PostgreSQL / Moodle | `localhost:5432` |
| Fuente transaccional | SQL Server | `localhost:1433` |
| Exploración de datos | DbGate | http://localhost:3000 |
| Lakehouse | MinIO API / consola | `localhost:9000` / http://localhost:9001 |
| Federación | Dremio | http://localhost:9047 |
| Búsqueda | OpenSearch | http://localhost:9200 |
| IA / RAG | Langflow | http://localhost:7860 |
| Gobierno | OpenMetadata | http://localhost:8585 |

La red Docker interna se llama `poc-university-network`. Los inicializadores crean los buckets de MinIO y la base/migraciones de OpenMetadata antes de iniciar sus dependencias.

## Requisitos

- Docker Engine 24 o superior.
- Docker Compose v2.
- GNU Make.
- `curl` para las comprobaciones de salud.
- `jq` para automatizaciones locales de la API de Dremio.

## Inicio rápido

```bash
make config
make up
make health
make seed
make seed-verify
```

`make seed` carga datos sintéticos e idempotentes para el ejercicio práctico: actividad académica en `moodle_db` (esquema `moodle`), SIS en `sis_db` (esquema `sis`) y facturación ERPNext en `erpnext_db` de PostgreSQL (esquema `erp`). SIS y ERPNext comparten `student_id`; Moodle se vincula por correo institucional. Los esquemas representan sus dominios y no sustituyen las aplicaciones oficiales. Cada nueva ejecución reemplaza solamente las tablas administradas de esos esquemas sintéticos.

## Exploración de datos

Después de cargar los datos, ejecuta `make gui` y abre http://localhost:3000. DbGate presenta las conexiones **Moodle**, **ERP legado MSSQL**, **SIS MSSQL** y **ERPNext PostgreSQL**, todas de solo lectura, para explorar tablas, relaciones y resultados SQL. El puerto está restringido a `localhost`; las conexiones usan el usuario local `lab_viewer`, limitado a consultas.

## Federación en Dremio

Dremio incluye los sources transaccionales `Moodle_Postgres`, `SIS_MSSQL` y `ERPNext_Postgres`, configurados con `lab_viewer` y, por tanto, solo lectura. También incluye `MinIO_Lakehouse`, un source S3 compatible limitado al bucket `university-lakehouse`.

El VDS `University_Lab.Student_360` consolida SIS, Moodle y ERPNext en una vista por estudiante con estado académico, matrícula, cuenta Moodle y facturación. En el editor SQL de Dremio se pueden consultar, por ejemplo:

```sql
SELECT COUNT(*) FROM "Moodle_Postgres".moodle.courses;
SELECT * FROM "University_Lab"."Student_360";
```

Consulta las URL y credenciales de desarrollo en [CREDENCIALES.md](CREDENCIALES.md). Dremio solicita crear su cuenta administradora en el primer acceso.

## Operación habitual

```bash
make ps                 # estado de los contenedores
make logs               # registros de todos los servicios
make logs SERVICES=minio
make restart            # reinicio controlado del stack
make down               # detiene y elimina contenedores/red, preserva datos
```

Consulta [OPERATIONS.md](OPERATIONS.md) para los comandos disponibles y el procedimiento de verificación.

## Desarrollo y contribución

Las contribuciones son bienvenidas. Lee el [glosario canónico](CONTEXT.md), [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) y [SECURITY.md](SECURITY.md) antes de abrir un issue o pull request.

## Preparación para publicación open source

Antes de publicar el repositorio:

1. Elige y añade una licencia aprobada por las personas titulares del proyecto.
2. Sustituye todas las contraseñas de desarrollo y evita publicar secretos reales.
3. Revisa qué puertos deben exponerse y habilita autenticación/TLS para cualquier despliegue fuera del equipo local.
4. Ejecuta `make check` en un entorno limpio.

## Licencia

Todavía no se ha seleccionado una licencia para este repositorio. Hasta añadir un archivo `LICENSE`, los derechos de uso, modificación y distribución no se conceden automáticamente.
