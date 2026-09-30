# ADR 0004: Catalogación de los activos de consumo (dashboards, corpus y asistente)

**Estado: aceptada.**

## Contexto

Los entregables 4–6 añadieron activos de consumo que OpenMetadata no cubría: tableros Metabase, el índice vectorial del corpus (`corpus_chunks` en OpenSearch) y el bucket documental (`openrag-docs` en MinIO). La regla de gobierno exige que todo activo consumible tenga owner, descripción y ubicación en el catálogo.

## Decisión

1. **Dashboards Metabase:** se registra el servicio `Metabase_Institutional` (Dashboard Service, tipo Metabase) con los tres tableros como entidades `Dashboard` con `sourceUrl`, owner y descripción. La ingesta vía conector de Airflow queda como mejora; el bootstrap REST es idempotente.
2. **Índice vectorial:** se registra el servicio `Corpus_Search` (Search Service, tipo OpenSearch) con el índice `corpus_chunks` como entidad `SearchIndex`, declarando sus campos de citación (`text`, `document`, `title`, `source`, `date`, `classification`, `audience`, `chunk`, `embedding`). Tipos válidos en 1.3.1: `TEXT`, `DATE`, `INTEGER`, `ARRAY` (no `STRING` ni `VECTOR`).
3. **Bucket documental:** se registra `Corpus_Storage` (Storage Service, tipo S3 con `awsConfig` y `endPointURL` hacia MinIO) y el contenedor `openrag_docs_corpus` (prefijo `corpus`).
4. **Asistente IA:** OpenMetadata 1.3.1 no tiene tipo API Service; el asistente se documenta operativamente en [OPERATIONS.md](../../OPERATIONS.md) y se revisará su catalogación al actualizar OpenMetadata.

Todo se ejecuta con `make metadata-consumption-sync` (bootstrap REST idempotente, mismo patrón del ADR 0001) y se verifica con los controles `activos-consumo` y `lineage-consumo` de `make metadata-verify`.

## Linage completo de la cadena de consumo

El bootstrap publica además el lineage de extremo a extremo (27 aristas): fuentes transaccionales → Silver → Gold → dashboards Metabase, y contenedor documental → índice vectorial. Así el linaje cubre desde el dato transaccional hasta el consumo en dashboard y asistente, verificable navegando en OpenMetadata a profundidad 3 desde cualquier tablero. Las dos tablas nuevas del seed (`sis.academic_registrations`, `erp.registration_payments`) se gobiernan de forma declarativa mediante `spec.tables` en sus manifiestos, aplicado por `make metadata-apply`.

## Glosario, domains, pipelines y charts

El mismo bootstrap completa la capa semántica y operativa:

- **Glosario `Universidad`:** 14 términos canónicos (CONTEXT.md + contrato de KPIs D-01, F-01–F-03).
- **Domains (Consumer-aligned):** `Rectoria`, `VR_Academica`, `VR_Financiera`, `Decanatos`; asignados a sus tres tableros Metabase.
- **Pipelines:** servicio `Airflow_Ingestion` con las 6 entidades `Pipeline` (4 ingestas de metadatos + 2 DAGs de Dremio Federation) con horario y propósito documentados.
- **Charts:** las 5 tarjetas Metabase como entidades `Chart` vinculadas a sus tableros, con su dataset `Gold_*` en la descripción.

`make metadata-verify` incluye el control `gobierno-semanticas` (mínimos: 14 términos, 4 domains, 6 pipelines, 5 charts) y `lineage-consumo`.

## Consecuencias

- El inventario del catálogo cubre ahora toda la cadena: fuentes → medallion → dashboards → corpus → índice.
- Los servicios se registran sin ingestas programadas: sus entidades son declarativas (owner, descripción, URL); sincronizar cambios requiere re-ejecutar el bootstrap, igual que el Dremio federado.
- Las credenciales Metabase/MinIO dentro de la configuración del servicio son de desarrollo; en producción usar secretos del entorno de ingesta.
