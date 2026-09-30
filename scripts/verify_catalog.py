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
SCHEMAS = {"Moodle_Postgres.moodle_db.moodle", "ERP_MSSQL.erpnext_db.erp", "SIS_MSSQL.sis_db.sis", "ERPNext_Postgres.erpnext_db.erp", "Dremio_Federation.Dremio.University_Lab"}
STUDENT_360 = "Dremio_Federation.Dremio.University_Lab.Student_360"
LINEAGE_UPSTREAM = {"SIS_MSSQL.sis_db.sis.students", "SIS_MSSQL.sis_db.sis.enrollments", "Moodle_Postgres.moodle_db.moodle.users", "ERPNext_Postgres.erpnext_db.erp.student_invoices"}
METADATA_DAGS = {f"{service}_metadata" for service in ("Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres")}
PROFILER_DAGS = {f"{service}_profiler" for service in ("Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres")}


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
    inventory = result("FAIL", "inventario", "; ".join(missing_inventory)) if missing_inventory else result("PASS", "inventario", "5 servicios, 5 bases y 5 esquemas esperados")
    transaccionals = [table for table in entities["tables"] if table.get("fullyQualifiedName") != STUDENT_360]
    assets = entities["databases"] + entities["schemas"] + entities["tables"]
    incomplete = [entity.get("fullyQualifiedName", entity.get("name", "<sin nombre>")) for entity in assets if not isinstance(entity.get("owner"), dict) or not entity["owner"].get("name") or not isinstance(entity.get("description"), str) or not entity["description"].strip()]
    governance = result("FAIL", "owner-y-descripción", ", ".join(incomplete)) if incomplete else result("PASS", "owner-y-descripción", f"{len(assets)} activos con owner y descripción")
    table_status = result("PASS", "tablas-y-vista", "18 tablas transaccionales y Student_360") if len(transaccionals) == 18 and STUDENT_360 in tables else result("FAIL", "tablas-y-vista", f"se esperaban 18 tablas transaccionales y {STUDENT_360}")
    return [inventory, governance, table_status]


def get_json(url: str, token: str) -> Any:
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"No se pudo consultar {url}: {error}") from error


def fetch_entities(api_url: str, token: str, endpoint: str) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params = {"limit": "100", "fields": "owner,description,tags"}
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
    if missing or len(dq_dags) != 18:
        detail = (f"faltan: {', '.join(sorted(missing))}; " if missing else "") + f"DAGs DQ encontrados: {len(dq_dags)}/18"
        return result("FAIL", "DAGs", detail)
    if states is not None:
        failed = sorted(dag for dag in expected | dq_dags if states.get(dag) != "success")
        if failed:
            return result("FAIL", "DAGs", f"última ejecución no exitosa: {', '.join(failed)}")
    return result("PASS", "DAGs", "4 metadata, 4 profiler, 18 DQ y 2 Dremio")


def verify_lineage(payload: dict[str, Any]) -> dict[str, str]:
    nodes = payload.get("nodes") if isinstance(payload, dict) else []
    names = {node.get("fullyQualifiedName") for node in nodes if isinstance(node, dict)}
    missing = LINEAGE_UPSTREAM - names
    return result("FAIL", "lineage-Student_360", _missing(LINEAGE_UPSTREAM, names)) if missing else result("PASS", "lineage-Student_360", "4 fuentes upstream aprobadas")


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
        entities = {"services": fetch_entities(args.api_url, args.token, "services/databaseServices"), "databases": fetch_entities(args.api_url, args.token, "databases"), "schemas": fetch_entities(args.api_url, args.token, "databaseSchemas"), "tables": fetch_entities(args.api_url, args.token, "tables")}
        checks = verify_inventory(entities)
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
