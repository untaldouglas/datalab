#!/usr/bin/env python3
"""Verifica en modo lectura el inventario y la operación del catálogo."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

try:
    from scripts.plan_catalog import DEFAULT_API_URL
except ModuleNotFoundError:
    from plan_catalog import DEFAULT_API_URL


SERVICES = {"Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres", "Dremio_Federation"}
DATABASES = {"Moodle_Postgres.moodle_db", "ERP_MSSQL.erpnext_db", "SIS_MSSQL.sis_db", "ERPNext_Postgres.erpnext_db", "Dremio_Federation.Dremio"}
SCHEMAS = {"Moodle_Postgres.moodle_db.moodle", "ERP_MSSQL.erpnext_db.erp", "SIS_MSSQL.sis_db.sis", "ERPNext_Postgres.erpnext_db.erp", "Dremio_Federation.Dremio.University_Lab", "Dremio_Federation.Dremio.Silver", "Dremio_Federation.Dremio.Gold_Rectoria", "Dremio_Federation.Dremio.Gold_Decanatos", "Dremio_Federation.Dremio.Gold_VR_Financiera"}
STUDENT_360 = "Dremio_Federation.Dremio.University_Lab.Student_360"
MEDALLION_VIEWS = {
    "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity",
    "Dremio_Federation.Dremio.Silver.Academic_Activity_Events",
    "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff",
    "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary",
    "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Financial_Summary",
    "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation",
    "Dremio_Federation.Dremio.Gold_VR_Financiera.Financial_Collection_Summary",
    "Dremio_Federation.Dremio.Gold_VR_Financiera.Monthly_Collection",
}
LINEAGE_UPSTREAM = {"SIS_MSSQL.sis_db.sis.students", "SIS_MSSQL.sis_db.sis.enrollments", "Moodle_Postgres.moodle_db.moodle.users", "ERPNext_Postgres.erpnext_db.erp.student_invoices"}
METADATA_DAGS = {f"{service}_metadata" for service in ("Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres")}
PROFILER_DAGS = {f"{service}_profiler" for service in ("Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres")}
CONSUMPTION_ASSETS = {
    "Metabase_Institutional.Tablero_Rectoria",
    "Metabase_Institutional.Tablero_Decanatos",
    "Metabase_Institutional.Tablero_VR_Financiera",
    "Corpus_Search.corpus_chunks",
    "Corpus_Storage.openrag_docs_corpus",
}
CONSUMPTION_ENDPOINTS = (("dashboards", {"Metabase_Institutional"}), ("searchIndexes", {"Corpus_Search"}), ("containers", {"Corpus_Storage"}))
SEMANTIC_EXPECTATIONS = {"glossaryTerms": 14, "domains": 4, "pipelines": 6, "charts": 5}


def result(status: str, control: str, detail: str) -> dict[str, str]:
    return {"status": status, "control": control, "detail": detail}


def _fqn_set(entities: list[dict[str, Any]]) -> set[str]:
    return {entity["fullyQualifiedName"] for entity in entities if isinstance(entity.get("fullyQualifiedName"), str)}


def _missing(expected: set[str], actual: set[str]) -> str:
    return ", ".join(sorted(expected - actual))


def verify_inventory(entities: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    service_names = {entity["name"] for entity in entities["services"] if isinstance(entity.get("name"), str)}
    databases = _fqn_set(entities["databases"])
    schemas = _fqn_set(entities["schemas"])
    tables = _fqn_set(entities["tables"])
    expected_inventory = (("servicios", SERVICES, service_names), ("bases", DATABASES, databases), ("esquemas", SCHEMAS, schemas))
    missing_inventory = [f"{label}: {_missing(expected, actual)}" for label, expected, actual in expected_inventory if expected - actual]
    inventory = result("FAIL", "inventario", "; ".join(missing_inventory)) if missing_inventory else result("PASS", "inventario", "5 servicios, 5 bases y 9 esquemas esperados")
    transaccionals = [table for table in entities["tables"] if table.get("fullyQualifiedName") not in MEDALLION_VIEWS | {STUDENT_360}]
    assets = entities["databases"] + entities["schemas"] + entities["tables"]
    incomplete = [entity.get("fullyQualifiedName", entity.get("name", "<sin nombre>")) for entity in assets if not isinstance(entity.get("owner"), dict) or not entity["owner"].get("name") or not isinstance(entity.get("description"), str) or not entity["description"].strip()]
    governance = result("FAIL", "owner-y-descripción", ", ".join(incomplete)) if incomplete else result("PASS", "owner-y-descripción", f"{len(assets)} activos con owner y descripción")
    tables = _fqn_set(entities["tables"])
    expected_dremio = MEDALLION_VIEWS | {STUDENT_360}
    if len(transaccionals) == 20 and expected_dremio <= tables:
        table_status = result("PASS", "tablas-y-vistas", "20 tablas transaccionales, Student_360 y 8 vistas medallion")
    else:
        table_status = result("FAIL", "tablas-y-vistas", f"se esperaban 20 tablas transaccionales, {STUDENT_360} y las vistas medallion; faltan: {_missing(expected_dremio, tables)}")
    return [inventory, governance, table_status]


def get_json(url: str, token: str) -> Any:
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"No se pudo consultar {url}: {error}") from error


def fetch_entities(api_url: str, token: str, endpoint: str, fields: str = "owner,description,tags") -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params = {"limit": "100", "fields": fields}
        if after:
            params["after"] = after
        payload = get_json(f"{api_url.rstrip('/')}/{endpoint}?{urlencode(params)}", token)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise RuntimeError(f"Respuesta inválida al consultar {endpoint}")
        entities.extend(item for item in data if isinstance(item, dict))
        paging = payload.get("paging") if isinstance(payload, dict) else None
        after = paging.get("after") if isinstance(paging, dict) else None
        if not after:
            return entities


def airflow_json(airflow_url: str, username: str, password: str, path: str) -> dict[str, Any]:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    request = Request(f"{airflow_url.rstrip('/')}/api/v1/{path}", headers={"Authorization": f"Basic {credentials}", "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"No se pudo consultar Airflow: {error}") from error
    return payload


def fetch_airflow_dags(airflow_url: str, username: str, password: str) -> set[str]:
    payload = airflow_json(airflow_url, username, password, "dags?limit=100")
    return {dag["dag_id"] for dag in payload.get("dags", []) if isinstance(dag, dict) and isinstance(dag.get("dag_id"), str)}


def fetch_airflow_states(airflow_url: str, username: str, password: str, dags: set[str]) -> dict[str, str | None]:
    states: dict[str, str | None] = {}
    for dag in dags:
        payload = airflow_json(airflow_url, username, password, f"dags/{quote(dag, safe='')}/dagRuns?limit=1&order_by=-execution_date")
        runs = payload.get("dag_runs") if isinstance(payload, dict) else None
        states[dag] = runs[0].get("state") if isinstance(runs, list) and runs and isinstance(runs[0], dict) else None
    return states


def verify_airflow(dags: set[str], states: dict[str, str | None] | None = None) -> dict[str, str]:
    expected = METADATA_DAGS | PROFILER_DAGS | {"Dremio_Federation_lineage", "Dremio_Federation_usage"}
    dq_dags = {dag for dag in dags if dag.endswith("_dq")}
    missing = expected - dags
    if missing or len(dq_dags) != 20:
        detail = (f"faltan: {', '.join(sorted(missing))}; " if missing else "") + f"DAGs DQ encontrados: {len(dq_dags)}/20"
        return result("FAIL", "DAGs", detail)
    if states is not None:
        failed = sorted(dag for dag in expected | dq_dags if states.get(dag) != "success")
        if failed:
            return result("FAIL", "DAGs", f"última ejecución no exitosa: {', '.join(failed)}")
    return result("PASS", "DAGs", "4 metadata, 4 profiler, 20 DQ y 2 Dremio")


def verify_lineage(payload: dict[str, Any]) -> dict[str, str]:
    nodes = payload.get("nodes") if isinstance(payload, dict) else []
    names = {node.get("fullyQualifiedName") for node in nodes if isinstance(node, dict)}
    missing = LINEAGE_UPSTREAM - names
    return result("FAIL", "lineage-Student_360", _missing(LINEAGE_UPSTREAM, names)) if missing else result("PASS", "lineage-Student_360", "4 fuentes upstream aprobadas")


def verify_consumption(entities: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    found = set()
    for endpoint, _ in CONSUMPTION_ENDPOINTS:
        found |= _fqn_set(entities.get(endpoint, []))
    missing = CONSUMPTION_ASSETS - found
    if missing:
        return result("FAIL", "activos-consumo", _missing(CONSUMPTION_ASSETS, found))
    return result("PASS", "activos-consumo", "3 tableros Metabase, índice corpus y bucket documental catalogados")


def verify_consumption_lineage(api_url: str, token: str) -> dict[str, str]:
    """Verifica que los dashboards y el índice corpus tengan lineage hacia su origen."""
    checks = {
        "Metabase_Institutional.Tablero_Rectoria": ("dashboard", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary"),
        "Corpus_Search.corpus_chunks": ("searchIndex", "Corpus_Storage.openrag_docs_corpus"),
    }
    for fqn, (endpoint, expected_upstream) in checks.items():
        try:
            payload = get_json(f"{api_url.rstrip('/')}/lineage/{endpoint}/name/{quote(fqn, safe='')}?upstreamDepth=1&downstreamDepth=0", token)
        except RuntimeError:
            return result("FAIL", "lineage-consumo", f"no se pudo consultar lineage de {fqn}")
        nodes = {node.get("fullyQualifiedName") for node in payload.get("nodes", []) if isinstance(node, dict)}
        if expected_upstream not in nodes:
            return result("FAIL", "lineage-consumo", f"{fqn} no tiene como origen {expected_upstream}")
    return result("PASS", "lineage-consumo", "tableros ligados a Gold y corpus ligado al bucket documental")


def verify_semantic_governance(entities: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    counts = {endpoint: len(entities.get(endpoint, [])) for endpoint in SEMANTIC_EXPECTATIONS}
    missing = {endpoint: expected for endpoint, expected in SEMANTIC_EXPECTATIONS.items() if counts[endpoint] < expected}
    if missing:
        detail = ", ".join(f"{endpoint}: {counts[endpoint]}/{expected}" for endpoint, expected in missing.items())
        return result("FAIL", "gobierno-semanticas", f"insuficientes: {detail}")
    detail = ", ".join(f"{endpoint}: {counts[endpoint]}" for endpoint in SEMANTIC_EXPECTATIONS)
    return result("PASS", "gobierno-semanticas", f"glosario, domains, pipelines y charts catalogados ({detail})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default=os.environ.get("OPENMETADATA_API_URL", DEFAULT_API_URL))
    parser.add_argument("--token", default=os.environ.get("OPENMETADATA_JWT_TOKEN"))
    parser.add_argument("--airflow-url", default=os.environ.get("AIRFLOW_API_URL", "http://localhost:8080"))
    parser.add_argument("--airflow-username", default=os.environ.get("AIRFLOW_USERNAME"))
    parser.add_argument("--airflow-password", default=os.environ.get("AIRFLOW_PASSWORD"))
    args = parser.parse_args(argv)
    if not args.token or not args.airflow_username or not args.airflow_password:
        parser.error("se requieren OPENMETADATA_JWT_TOKEN, AIRFLOW_USERNAME y AIRFLOW_PASSWORD sólo en el entorno de ejecución")
    try:
        entities = {"services": fetch_entities(args.api_url, args.token, "services/databaseServices"), "databases": fetch_entities(args.api_url, args.token, "databases"), "schemas": fetch_entities(args.api_url, args.token, "databaseSchemas"), "tables": fetch_entities(args.api_url, args.token, "tables"), **{endpoint: fetch_entities(args.api_url, args.token, endpoint) for endpoint, _ in CONSUMPTION_ENDPOINTS}, **{endpoint: fetch_entities(args.api_url, args.token, endpoint, fields="owner,description") for endpoint in SEMANTIC_EXPECTATIONS}}
        checks = verify_inventory(entities)
        checks.append(verify_consumption(entities))
        checks.append(verify_consumption_lineage(args.api_url, args.token))
        checks.append(verify_semantic_governance(entities))
        dags = fetch_airflow_dags(args.airflow_url, args.airflow_username, args.airflow_password)
        checks.append(verify_airflow(dags, fetch_airflow_states(args.airflow_url, args.airflow_username, args.airflow_password, METADATA_DAGS | PROFILER_DAGS | {"Dremio_Federation_lineage", "Dremio_Federation_usage"} | {dag for dag in dags if dag.endswith("_dq")})))
        lineage = get_json(f"{args.api_url.rstrip('/')}/lineage/table/name/{quote(STUDENT_360, safe='')}?upstreamDepth=1&downstreamDepth=0", args.token)
        checks.append(verify_lineage(lineage))
        checks.append(result("OUT_OF_SCOPE", "clasificación-descendiente", "Database, Schema y Table/View no reciben clasificación automática en fase 4"))
    except RuntimeError as error:
        print(f"metadata-verify: {error}", file=sys.stderr)
        return 1
    for check in checks:
        print(f"{check['status']:12} {check['control']}: {check['detail']}")
    return 1 if any(check["status"] == "FAIL" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
