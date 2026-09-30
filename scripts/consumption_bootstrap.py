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


def main():
    om = om_session()
    api = os.environ["OPENMETADATA_API_URL"]
    owner = admin_owner(om, api)
    ensure_dashboard_service(om, api, owner)
    ensure_search_service(om, api, owner)
    ensure_storage_service(om, api, owner)
    print(f"Activos de consumo catalogados ({dt.date.today().isoformat()}).")


if __name__ == "__main__":
    main()
