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


ENTITY_ENDPOINTS = {"table": "tables", "dashboard": "dashboards", "searchIndex": "searchIndexes", "container": "containers", "domain": "domains", "chart": "charts", "glossaryTerm": "glossaryTerms", "pipeline": "pipelines"}


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


GLOSSARY_NAME = "Universidad"
GLOSSARY_TERMS = [
    ("metrica_institucional", "Métrica institucional", "Agregado con fórmula, fuente de verdad, owner, fecha de corte y granularidad aprobadas para apoyar una decisión institucional."),
    ("fecha_de_corte", "Fecha de corte", "Instante hasta el cual se consideran los datos de una métrica o respuesta analítica."),
    ("ventana_de_participacion", "Ventana de participación", "Periodo móvil de cuatro semanas calendario inmediatamente anteriores a la fecha de corte."),
    ("corte_financiero", "Corte financiero", "Instante al que se calcula el saldo pendiente o vencido; la emisión se asigna al semestre por fecha de factura y el cobro por fecha real de pago."),
    ("estudiante_elegible", "Estudiante elegible", "Estudiante con matrícula vigente y pago de matrícula paid o partial."),
    ("elegibilidad_temporal", "Elegibilidad temporal", "Habilitación para cursar concedida con pago parcial mientras la matrícula permanezca vigente al corte."),
    ("semestre_academico", "Semestre académico", "Periodo institucional: el impar va de enero a julio y el par de agosto a diciembre."),
    ("facultad", "Facultad", "Unidad organizativa responsable de una serie de servicios formativos de pregrado."),
    ("programa_formativo", "Programa formativo", "Oferta académica vigente perteneciente a una facultad."),
    ("servicio_formativo", "Servicio formativo", "Curso u oferta cursable asociado a un programa formativo vigente."),
    ("cobertura_de_integracion", "Cobertura de integración", "Proporción o conteo agregado de registros enlazados entre fuentes aprobadas; no mide calidad ni éxito académico."),
    ("participacion_academica", "Participación académica", "Porcentaje de estudiantes elegibles con al menos un evento válido en la ventana de participación (D-01, R-01/R-03)."),
    ("tasa_de_cobro", "Tasa de cobro", "Cociente entre monto pagado y monto facturado al corte financiero (F-02)."),
    ("cobros_por_periodo", "Cobros por periodo", "Conteo y suma de pagos con estado paid o partial agrupados por mes de paid_at (F-03)."),
]

DOMAINS = [
    ("Rectoria", "Rectoría", "Domain de Rectoría: evolución académica y financiera institucional."),
    ("VR_Academica", "Vicerrectoría Académica", "Domain de VR Académica: participación y avance por programas y cursos."),
    ("VR_Financiera", "Vicerrectoría Financiera", "Domain de VR Financiera: facturación, saldo pendiente y cobranza."),
    ("Decanatos", "Decanatos", "Domain de Decanatos: comportamiento de programas, cursos y estudiantes por facultad."),
]

DASHBOARD_DOMAINS = {
    "Tablero_Rectoria": "Rectoria",
    "Tablero_Decanatos": "Decanatos",
    "Tablero_VR_Financiera": "VR_Financiera",
}

CHARTS = [
    ("Chart_Participacion_Facultad", "Participación académica por facultad", "Rectoría",
     "Participación de estudiantes elegibles por facultad (Gold_Rectoria.Rectoral_Academic_Summary)."),
    ("Chart_Estado_Financiero_Semestre", "Estado financiero por semestre", "Rectoría",
     "Facturación, cobro y saldo por semestre (Gold_Rectoria.Rectoral_Financial_Summary)."),
    ("Chart_Participacion_Programa", "Participación por programa", "Decanatos",
     "Participación agregada por facultad y programa (Gold_Decanatos.Decanato_Program_Participation, D-01)."),
    ("Chart_Financiero_Semestre_VR", "Estado financiero por semestre (VR Financiera)", "VR Financiera",
     "Facturación, cobro, saldo y tasa de cobro por semestre (Gold_VR_Financiera.Financial_Collection_Summary, F-01/F-02)."),
    ("Chart_Cobros_Mes", "Cobros por mes", "VR Financiera",
     "Pagos registrados por mes de fecha real de pago (Gold_VR_Financiera.Monthly_Collection, F-03)."),
]

PIPELINES = [
    ("Moodle_Postgres_metadata", "Ingesta de metadatos de Moodle (diaria 02:00)."),
    ("ERP_MSSQL_metadata", "Ingesta de metadatos del ERP legado MSSQL (diaria 02:05)."),
    ("SIS_MSSQL_metadata", "Ingesta de metadatos del SIS MSSQL (diaria 02:10)."),
    ("ERPNext_Postgres_metadata", "Ingesta de metadatos de ERPNext (diaria 02:15)."),
    ("Dremio_Federation_lineage", "Publica el lineage de Student_360 hacia las cuatro fuentes aprobadas (diaria 04:30)."),
    ("Dremio_Federation_usage", "Publica el uso diario de Student_360 desde sys.jobs_recent (diaria 04:45)."),
]


def ensure_glossary(om, api, owner):
    post_if_missing(om, f"{api}/glossaries", {
        "name": GLOSSARY_NAME, "displayName": "Glosario Universidad",
        "description": "Términos canónicos de la plataforma de datos universitaria (CONTEXT.md y contrato de KPIs).",
        "owner": owner,
    })
    for name, display, description in GLOSSARY_TERMS:
        post_if_missing(om, f"{api}/glossaryTerms", {
            "glossary": GLOSSARY_NAME, "name": name, "displayName": display,
            "description": description, "owner": owner,
        })
    print(f"Glosario {GLOSSARY_NAME}: {len(GLOSSARY_TERMS)} términos catalogados.")


def ensure_domains(om, api, owner):
    for name, display, description in DOMAINS:
        post_if_missing(om, f"{api}/domains", {
            "name": name, "displayName": display, "description": description,
            "domainType": "Consumer-aligned", "owner": owner,
        })
    for dashboard_name, domain_name in DASHBOARD_DOMAINS.items():
        dashboard = resolve_entity(om, api, "dashboard", f"Metabase_Institutional.{dashboard_name}")
        if isinstance(dashboard.get("domain"), dict) and dashboard["domain"].get("id"):
            continue
        domain = resolve_entity(om, api, "domain", domain_name)
        operations = [{"op": "add", "path": "/domain", "value": {"id": domain["id"], "type": "domain"}}]
        response = om.patch(f"{api}/dashboards/{dashboard['id']}", json=operations,
                            headers={"Content-Type": "application/json-patch+json"}, timeout=30)
        response.raise_for_status()
    print(f"Domains creados: {len(DOMAINS)}; tableros asignados: {len(DASHBOARD_DOMAINS)}.")


def ensure_pipelines(om, api, owner):
    post_if_missing(om, f"{api}/services/pipelineServices", {
        "name": "Airflow_Ingestion", "displayName": "Airflow Ingestion",
        "serviceType": "Airflow", "owner": owner,
        "description": "Ejecutor de ingestas y sincronizaciones de la POC (Apache Airflow gestionado por OpenMetadata).",
        "connection": {"config": {"type": "Airflow", "hostPort": "http://ingestion:8080"}},
    })
    for name, description in PIPELINES:
        post_if_missing(om, f"{api}/pipelines", {
            "name": name, "displayName": name, "service": "Airflow_Ingestion",
            "owner": owner, "description": description,
        })
    print(f"Pipelines catalogados: {len(PIPELINES)}.")


def ensure_charts(om, api, owner):
    for name, display, audience, description in CHARTS:
        post_if_missing(om, f"{api}/charts", {
            "name": name, "displayName": display, "service": "Metabase_Institutional",
            "owner": owner, "description": f"[{audience}] {description}",
            "chartType": "Bar",
        })
    by_display = {display: name for name, display, _, _ in CHARTS}
    dashboard_charts = {
        "Tablero_Rectoria": ["Participación académica por facultad", "Estado financiero por semestre"],
        "Tablero_Decanatos": ["Participación por programa"],
        "Tablero_VR_Financiera": ["Estado financiero por semestre (VR Financiera)", "Cobros por mes"],
    }
    for dashboard_name, displays in dashboard_charts.items():
        dashboard = resolve_entity(om, api, "dashboard", f"Metabase_Institutional.{dashboard_name}")
        if dashboard.get("charts"):
            continue
        references = [{"id": resolve_entity(om, api, "chart", f"Metabase_Institutional.{by_display[d]}")["id"], "type": "chart"} for d in displays]
        response = om.patch(f"{api}/dashboards/{dashboard['id']}",
                            json=[{"op": "add", "path": "/charts", "value": references}],
                            headers={"Content-Type": "application/json-patch+json"}, timeout=30)
        response.raise_for_status()
    print(f"Charts catalogados: {len(CHARTS)} y vinculados a sus tableros.")


def main():
    om = om_session()
    api = os.environ["OPENMETADATA_API_URL"]
    owner = admin_owner(om, api)
    ensure_dashboard_service(om, api, owner)
    ensure_search_service(om, api, owner)
    ensure_storage_service(om, api, owner)
    ensure_lineage(om, api)
    ensure_glossary(om, api, owner)
    ensure_domains(om, api, owner)
    ensure_pipelines(om, api, owner)
    ensure_charts(om, api, owner)
    print(f"Activos de consumo catalogados ({dt.date.today().isoformat()}).")


if __name__ == "__main__":
    main()
