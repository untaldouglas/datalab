#!/usr/bin/env python3
"""Cataloga en OpenMetadata los activos de consumo: dashboards Metabase,
índice vectorial del corpus (OpenSearch) y bucket documental (MinIO).

Mismo espíritu que el ADR 0001: los servicios se registran con sus entidades
mínimas (owner, descripción, URL) por REST, de forma idempotente, sin depender
de desplegar ingestas desde la interfaz. El asistente IA no es catalogable en
OpenMetadata 1.3.1 (sin API Services); se documenta en el ADR 0004.
"""
import datetime as dt
import os
import urllib.parse

from dremio_openmetadata_sync import om_session, post_if_missing


def admin_owner(om, api):
    admin = om.get(f"{api}/users/name/admin", timeout=30).json()
    return {"id": admin["id"], "type": "user"}


def ensure_dashboard_service(om, api, owner):
    post_if_missing(om, f"{api}/services/dashboardServices", {
        "name": "Metabase_Institutional", "displayName": "Metabase Institutional",
        "serviceType": "Metabase", "owner": owner,
        "description": "Capa BI de la POC: tableros por audiencia construidos sobre los espacios Gold_*.",
        "connection": {"config": {
            "type": "Metabase", "hostPort": "http://metabase:3000",
            "username": os.environ.get("METABASE_USER", "admin@datalab.local"),
            "password": os.environ.get("METABASE_PASSWORD", "MetabaseAdmin123!"),
        }},
    })
    base = "Metabase_Institutional"
    dashboards = [
        ("Tablero_Rectoria", "Tablero Rectoría",
         "Resúmenes académico y financiero de Gold_Rectoria (R-01 a R-07).",
         "http://localhost:3030/dashboard/1"),
        ("Tablero_Decanatos", "Tablero Decanatos",
         "Participación por programa (D-01) desde Gold_Decanatos.",
         "http://localhost:3030/dashboard/2"),
        ("Tablero_VR_Financiera", "Tablero VR Financiera",
         "Facturación, saldo pendiente y cobros por periodo (F-01 a F-03) desde Gold_VR_Financiera.",
         "http://localhost:3030/dashboard/3"),
    ]
    for name, display, description, url in dashboards:
        post_if_missing(om, f"{api}/dashboards", {
            "name": name, "displayName": display, "service": base,
            "owner": owner, "description": description, "sourceUrl": url,
        })


def ensure_search_service(om, api, owner):
    post_if_missing(om, f"{api}/services/searchServices", {
        "name": "Corpus_Search", "displayName": "Corpus Search",
        "serviceType": "OpenSearch", "owner": owner,
        "description": "Búsqueda del corpus documental institucional; índice vectorial k-NN.",
        "connection": {"config": {"type": "OpenSearch", "hostPort": "opensearch:9200"}},
    })
    fields = [
        ("text", "TEXT", "Fragmento del documento citable."),
        ("document", "TEXT", "Archivo markdown de origen del fragmento."),
        ("title", "TEXT", "Título del documento."),
        ("source", "TEXT", "Fuente institucional declarada del documento."),
        ("date", "DATE", "Fecha del documento."),
        ("classification", "TEXT", "Clasificación UniversityClassification del servicio."),
        ("audience", "TEXT", "Audiencias autorizadas."),
        ("chunk", "INTEGER", "Índice del fragmento dentro del documento."),
        ("embedding", "ARRAY", "Vector de 384 dimensiones para búsqueda k-NN."),
    ]
    post_if_missing(om, f"{api}/searchIndexes", {
        "name": "corpus_chunks", "displayName": "Corpus Chunks (vectorial)",
        "service": "Corpus_Search", "owner": owner,
        "description": "Índice del corpus documental: fragmentos con metadatos de citación y embedding de 384 dimensiones (paraphrase-multilingual-MiniLM-L12-v2).",
        "fields": [{"name": n, "dataType": t, "description": d} for n, t, d in fields],
    })


def ensure_storage_service(om, api, owner):
    post_if_missing(om, f"{api}/services/storageServices", {
        "name": "Corpus_Storage", "displayName": "Corpus Storage",
        "serviceType": "S3", "owner": owner,
        "description": "Almacenamiento S3-compatible (MinIO) del corpus documental; origen de verdad de los documentos.",
        "connection": {"config": {
            "type": "S3",
            "awsConfig": {
                "awsAccessKeyId": os.environ.get("MINIO_USER", "admin"),
                "awsSecretAccessKey": os.environ.get("MINIO_PASSWORD", "MinioPassword123!"),
                "awsRegion": "us-east-1",
                "endPointURL": "http://minio:9000",
            },
        }},
    })
    post_if_missing(om, f"{api}/containers", {
        "name": "openrag_docs_corpus", "displayName": "openrag-docs/corpus",
        "service": "Corpus_Storage", "owner": owner, "prefix": "corpus",
        "description": "Documentos sintéticos autorizados del corpus (8 markdown con frontmatter de citación).",
        "sourceUrl": "http://localhost:9001",
    })


ENTITY_ENDPOINTS = {"table": "tables", "dashboard": "dashboards", "searchIndex": "searchIndexes", "container": "containers"}


def resolve_entity(om, api, entity_type, fqn):
    """Resuelve una entidad por FQN (endpoint plural; /table/name es inválido)."""
    endpoint = ENTITY_ENDPOINTS[entity_type]
    response = om.get(f"{api}/{endpoint}/name/{urllib.parse.quote(fqn)}", timeout=30)
    response.raise_for_status()
    return response.json()


def publish_edge(om, api, from_entity, to_entity):
    return om.put(f"{api}/lineage", json={"edge": {
        "fromEntity": {"id": from_entity["id"], "type": from_entity["type"]},
        "toEntity": {"id": to_entity["id"], "type": to_entity["type"]},
    }}, timeout=30)


def ensure_lineage(om, api):
    """Lineage completo: transaccional → Silver → Gold → dashboards; contenedor → índice."""
    edges = [
        # Silver ← transaccional
        ("table", "SIS_MSSQL.sis_db.sis.students", "table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity"),
        ("table", "SIS_MSSQL.sis_db.sis.academic_registrations", "table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity"),
        ("table", "SIS_MSSQL.sis_db.sis.enrollments", "table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity"),
        ("table", "ERPNext_Postgres.erpnext_db.erp.registration_payments", "table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity"),
        ("table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity", "table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events"),
        ("table", "Moodle_Postgres.moodle_db.moodle.users", "table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events"),
        ("table", "Moodle_Postgres.moodle_db.moodle.assignment_submissions", "table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events"),
        ("table", "Moodle_Postgres.moodle_db.moodle.quiz_attempts", "table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events"),
        ("table", "Moodle_Postgres.moodle_db.moodle.forum_posts", "table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events"),
        # Gold ← Silver / transaccional
        ("table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity", "table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary"),
        ("table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events", "table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary"),
        ("table", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary"),
        ("table", "ERPNext_Postgres.erpnext_db.erp.student_invoices", "table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Financial_Summary"),
        ("table", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Financial_Summary"),
        ("table", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity", "table", "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation"),
        ("table", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events", "table", "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation"),
        ("table", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "table", "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation"),
        ("table", "ERPNext_Postgres.erpnext_db.erp.student_invoices", "table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Financial_Collection_Summary"),
        ("table", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Financial_Collection_Summary"),
        ("table", "ERPNext_Postgres.erpnext_db.erp.registration_payments", "table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Monthly_Collection"),
        ("table", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Monthly_Collection"),
        # Dashboards ← Gold
        ("table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary", "dashboard", "Metabase_Institutional.Tablero_Rectoria"),
        ("table", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Financial_Summary", "dashboard", "Metabase_Institutional.Tablero_Rectoria"),
        ("table", "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation", "dashboard", "Metabase_Institutional.Tablero_Decanatos"),
        ("table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Financial_Collection_Summary", "dashboard", "Metabase_Institutional.Tablero_VR_Financiera"),
        ("table", "Dremio_Federation.Dremio.Gold_VR_Financiera.Monthly_Collection", "dashboard", "Metabase_Institutional.Tablero_VR_Financiera"),
        # Corpus: contenedor documental → índice vectorial
        ("container", "Corpus_Storage.openrag_docs_corpus", "searchIndex", "Corpus_Search.corpus_chunks"),
    ]
    published = 0
    for from_type, from_fqn, to_type, to_fqn in edges:
        from_entity = resolve_entity(om, api, from_type, from_fqn)
        to_entity = resolve_entity(om, api, to_type, to_fqn)
        response = publish_edge(om, api, {**from_entity, "type": from_type}, {**to_entity, "type": to_type})
        response.raise_for_status()
        published += 1
    print(f"Lineage publicado: {published} aristas (fuentes → medallion → consumo).")

def main():
    om = om_session()
    api = os.environ["OPENMETADATA_API_URL"]
    owner = admin_owner(om, api)
    ensure_dashboard_service(om, api, owner)
    ensure_search_service(om, api, owner)
    ensure_storage_service(om, api, owner)
    ensure_lineage(om, api)
    print(f"Activos de consumo catalogados ({dt.date.today().isoformat()}).")


if __name__ == "__main__":
    main()
