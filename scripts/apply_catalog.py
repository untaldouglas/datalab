#!/usr/bin/env python3
"""Aplica de forma idempotente el gobierno declarado a servicios de OpenMetadata."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from scripts.plan_catalog import DEFAULT_API_URL, fetch_database_services, load_manifests
except ModuleNotFoundError:  # Ejecutado directamente desde scripts/.
    from plan_catalog import DEFAULT_API_URL, fetch_database_services, load_manifests


CLASSIFICATION = "UniversityClassification"
ROW_COUNT_TEST_CASE = "row_count_positive"
ROW_COUNT_TEST_DEFINITION = "tableRowCountToBeBetween"
ROW_COUNT_CASE_DESCRIPTION = "Verifica que la tabla tenga al menos un registro para detectar una carga o fuente vacía inesperada."
SUITE_DESCRIPTION = "Controles de calidad operativos declarados en el manifiesto de la fuente."
CLASSIFICATION_DESCRIPTION = "Clasificación de sensibilidad para los activos de la plataforma de datos universitaria."
TAG_DESCRIPTIONS = {
    "internal": "Datos de uso interno de la plataforma universitaria.",
    "confidential": "Datos confidenciales sujetos a controles reforzados.",
    "restricted": "Datos restringidos con acceso limitado por su sensibilidad.",
}


def managed_tag_fqn(manifest: dict[str, Any]) -> str:
    classification = manifest["spec"]["governance"]["classification"]
    return f"{CLASSIFICATION}.{classification.title()}"


def service_type_matches(manifest: dict[str, Any], service: dict[str, Any]) -> bool:
    actual = service.get("serviceType")
    return isinstance(actual, str) and actual.casefold() == manifest["spec"]["service"]["type"].casefold()


def _tag_fqn(tag: dict[str, Any]) -> str | None:
    value = tag.get("tagFQN")
    return value if isinstance(value, str) else None


def build_service_patch(manifest: dict[str, Any], service: dict[str, Any], desired_owner: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    desired_description = manifest["metadata"]["description"]
    if service.get("description") != desired_description:
        operations.append({"op": "replace", "path": "/description", "value": desired_description})
    current_owner = service.get("owner") if isinstance(service.get("owner"), dict) else {}
    if current_owner.get("id") != desired_owner.get("id"):
        operations.append({"op": "replace", "path": "/owner", "value": desired_owner})

    desired_tag = managed_tag_fqn(manifest)
    existing_tags = service.get("tags") if isinstance(service.get("tags"), list) else []
    retained = [tag for tag in existing_tags if isinstance(tag, dict) and not (_tag_fqn(tag) or "").startswith(f"{CLASSIFICATION}.")]
    desired_labels = [tag for tag in existing_tags if isinstance(tag, dict) and _tag_fqn(tag) == desired_tag]
    target_tags = retained + (desired_labels[:1] or [{"tagFQN": desired_tag, "labelType": "Manual", "state": "Confirmed"}])
    if existing_tags != target_tags:
        operations.append({"op": "replace", "path": "/tags", "value": target_tags})
    return operations


def request_json(method: str, url: str, token: str, payload: Any | None = None, content_type: str = "application/json", not_found_ok: bool = False) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=body, headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": content_type}, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response) if response.readable() else None
    except HTTPError as error:
        if error.code == 404 and not_found_ok:
            return None
        raise RuntimeError(f"OpenMetadata respondió HTTP {error.code} durante {method} {url}") from error
    except URLError as error:
        raise RuntimeError(f"No se pudo conectar con OpenMetadata: {error.reason}") from error


def ensure_governance_tags(api_url: str, token: str) -> None:
    base = api_url.rstrip("/")
    classification_url = f"{base}/classifications/name/{CLASSIFICATION}"
    if request_json("GET", classification_url, token, not_found_ok=True) is None:
        request_json("POST", f"{base}/classifications", token, {"name": CLASSIFICATION, "description": CLASSIFICATION_DESCRIPTION, "mutuallyExclusive": True})
    for name, description in TAG_DESCRIPTIONS.items():
        tag_name = name.title()
        tag_url = f"{base}/tags/name/{quote(f'{CLASSIFICATION}.{tag_name}', safe='')}"
        if request_json("GET", tag_url, token, not_found_ok=True) is None:
            request_json("POST", f"{base}/tags", token, {"name": tag_name, "classification": CLASSIFICATION, "description": description})


def fetch_owner(api_url: str, token: str, name: str) -> dict[str, Any]:
    owner = request_json("GET", f"{api_url.rstrip('/')}/users/name/{quote(name, safe='')}", token)
    if not isinstance(owner, dict) or not isinstance(owner.get("id"), str):
        raise RuntimeError(f"No se encontró el owner de usuario declarado: {name}")
    # validateOwner de OM 1.3 requiere type explícito; la respuesta de /users puede omitirlo.
    return {"id": owner["id"], "type": "user", "name": owner.get("name", name)}


def build_table_operations(table: dict[str, Any], current: dict[str, Any], owner: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    description = current.get("description")
    if not isinstance(description, str) or not description.strip():
        operations.append({"op": "add", "path": "/description", "value": table["description"]})
    elif description != table["description"]:
        operations.append({"op": "replace", "path": "/description", "value": table["description"]})
    owner_ref = current.get("owner") if isinstance(current.get("owner"), dict) else {}
    if not owner_ref.get("name"):
        operations.append({"op": "add", "path": "/owner", "value": owner})
    return operations


def apply_table_governance(manifests: list[dict[str, Any]], api_url: str, token: str, owner_name: str) -> list[dict[str, str]]:
    """Aplica owner y descripción declarados a las tablas de spec.tables."""
    results: list[dict[str, str]] = []
    owner = fetch_owner(api_url, token, owner_name)
    for manifest in manifests:
        service = manifest["spec"]["service"]["name"]
        for table in manifest["spec"].get("tables", []):
            fqn = f"{service}.{table['database']}.{table['schema']}.{table['name']}"
            current = request_json("GET", f"{api_url.rstrip('/')}/tables/name/{quote(fqn)}", token, not_found_ok=True)
            if current is None:
                results.append({"service": fqn, "action": "NOT_FOUND", "detail": "tabla ausente en el catálogo; ejecute su ingesta de metadatos"})
                continue
            operations = build_table_operations(table, current, owner)
            if not operations:
                results.append({"service": fqn, "action": "NO_CHANGE", "detail": ""})
                continue
            request_json("PATCH", f"{api_url.rstrip('/')}/tables/{current['id']}", token, operations, "application/json-patch+json")
            results.append({"service": fqn, "action": "UPDATED", "detail": ", ".join(operation["path"].removeprefix("/") for operation in operations)})
    return results


def quality_tables(manifests: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Pares (manifiesto, servicio, tabla) con calidad habilitada y control de fila declarado."""
    pairs: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for manifest in manifests:
        ingestion = manifest["spec"].get("ingestion", {})
        quality = ingestion.get("quality") if isinstance(ingestion, dict) else None
        if not isinstance(quality, dict) or not quality.get("enabled"):
            continue
        if ROW_COUNT_TEST_CASE not in (quality.get("initialTests") or []):
            continue
        service = manifest["spec"]["service"]
        for table in manifest["spec"].get("tables", []):
            pairs.append((manifest, service, table))
    return pairs


def ensure_quality_control(manifests: list[dict[str, Any]], api_url: str, token: str, services: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """Materializa suite ejecutable, caso de prueba y pipeline de calidad declarados."""
    base = api_url.rstrip("/")
    results: list[dict[str, str]] = []
    # OM 1.3 no soporta el filtro por servicio en ingestionPipelines; se lista una vez y se filtra en Python.
    pipelines_by_service: dict[str, set[str]] = {}
    for pipeline in request_json("GET", f"{base}/services/ingestionPipelines?limit=200", token).get("data", []):
        service = pipeline.get("service")
        if isinstance(pipeline.get("name"), str) and isinstance(service, dict) and isinstance(service.get("name"), str):
            pipelines_by_service.setdefault(service["name"], set()).add(pipeline["name"])
    for manifest, service_spec, table in quality_tables(manifests):
        service_name = service_spec["name"]
        service = services.get(service_name)
        if service is None or not isinstance(service.get("id"), str):
            results.append({"service": service_name, "action": "BLOCKED", "detail": f"tabla {table['name']} sin servicio de catálogo"})
            continue
        fqn = f"{service_name}.{table['database']}.{table['schema']}.{table['name']}"
        suite_fqn = f"{fqn}.testSuite"
        suite = request_json("GET", f"{base}/dataQuality/testSuites/name/{quote(suite_fqn, safe='')}", token, not_found_ok=True)
        if suite is None:
            # OM 1.3 crea suites ejecutables vía PUT /executable; el FQN lo deriva el servidor.
            suite = request_json("PUT", f"{base}/dataQuality/testSuites/executable", token, {
                "name": f"{fqn}.TestSuite",
                "description": SUITE_DESCRIPTION,
                "executableEntityReference": fqn,
            })
        case_fqn = f"{fqn}.{ROW_COUNT_TEST_CASE}"
        case = request_json("GET", f"{base}/dataQuality/testCases/name/{quote(case_fqn, safe='')}", token, not_found_ok=True)
        if case is None:
            request_json("POST", f"{base}/dataQuality/testCases", token, {
                "name": ROW_COUNT_TEST_CASE,
                "description": ROW_COUNT_CASE_DESCRIPTION,
                "testSuite": suite_fqn,
                "entityLink": f"<#E::table::{fqn}>",
                "testDefinition": ROW_COUNT_TEST_DEFINITION,
                "parameterValues": [{"name": "minValue", "value": "1"}],
            })
        pipeline_name = f"{service_name}_{table['name']}_dq"
        pipeline_names = pipelines_by_service.get(service_name, set())
        actions: list[str] = []
        if pipeline_name not in pipeline_names:
            schedule = manifest["spec"]["ingestion"]["quality"].get("schedule", "0 4 * * *")
            timezone = manifest["spec"]["ingestion"]["quality"].get("timezone", "America/El_Salvador")
            pipeline = request_json("POST", f"{base}/services/ingestionPipelines", token, {
                "name": pipeline_name,
                "displayName": pipeline_name,
                "pipelineType": "TestSuite",
                "sourceConfig": {"config": {"type": "TestSuite", "entityFullyQualifiedName": fqn}},
                "airflowConfig": {
                    "scheduleInterval": schedule,
                    "pipelineTimezone": timezone,
                    "concurrency": 1,
                    "retries": 1,
                    "retryDelay": 300,
                    "pipelineCatchup": False,
                    "pausePipeline": False,
                },
                "service": {"type": "databaseService", "id": service["id"]},
            })
            pipeline_id = pipeline.get("id") if isinstance(pipeline, dict) else None
            if isinstance(pipeline_id, str):
                # OM 1.3 despliega el DAG en Airflow sólo vía POST /deploy/{id}.
                request_json("POST", f"{base}/services/ingestionPipelines/deploy/{pipeline_id}", token)
            actions.append("calidad creada")
        results.append({"service": pipeline_name, "action": "UPDATED" if actions else "NO_CHANGE", "detail": ", ".join(actions)})
    return results


def apply_manifests(manifests: list[dict[str, Any]], api_url: str, token: str) -> list[dict[str, str]]:
    ensure_governance_tags(api_url, token)
    services: dict[str, dict[str, Any]] = {}
    for service in fetch_database_services(api_url, token):
        name = service.get("name")
        if isinstance(name, str):
            services[name] = service
    results: list[dict[str, str]] = []
    for manifest in manifests:
        name = manifest["spec"]["service"]["name"]
        service = services.get(name)
        if service is None:
            results.append({"service": name, "action": "BLOCKED", "detail": "no se crea sin una configuración de conexión y secreto aprobados"})
            continue
        if not service_type_matches(manifest, service):
            results.append({"service": name, "action": "BLOCKED", "detail": "el tipo de servicio difiere; cambiarlo requiere una configuración de conexión aprobada"})
            continue
        owner = fetch_owner(api_url, token, manifest["metadata"]["owner"])
        operations = build_service_patch(manifest, service, owner)
        if not operations:
            results.append({"service": name, "action": "NO_CHANGE", "detail": ""})
            continue
        identifier = service.get("id")
        if not isinstance(identifier, str):
            raise RuntimeError(f"El servicio {name} no contiene id para aplicar el parche")
        request_json("PATCH", f"{api_url.rstrip('/')}/services/databaseServices/{identifier}", token, operations, "application/json-patch+json")
        results.append({"service": name, "action": "UPDATED", "detail": ", ".join(operation["path"].removeprefix("/") for operation in operations)})
    results.extend(apply_table_governance(manifests, api_url, token, manifests[0]["metadata"]["owner"]))
    results.extend(ensure_quality_control(manifests, api_url, token, services))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", default="catalog/sources")
    parser.add_argument("--api-url", default=os.environ.get("OPENMETADATA_API_URL", DEFAULT_API_URL))
    parser.add_argument("--token", default=os.environ.get("OPENMETADATA_JWT_TOKEN"), help="JWT de OpenMetadata; también puede definirse en OPENMETADATA_JWT_TOKEN")
    parser.add_argument("--confirm", action="store_true", help="autoriza las mutaciones declaradas")
    args = parser.parse_args(argv)
    if not args.token:
        parser.error("se requiere --token o OPENMETADATA_JWT_TOKEN; el aplicador no obtiene ni almacena credenciales")
    if not args.confirm:
        parser.error("se requiere --confirm; ejecute metadata-plan y revise los cambios antes de aplicar")
    try:
        results = apply_manifests(load_manifests(Path(args.catalog_dir)), args.api_url, args.token)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"metadata-apply: {error}", file=sys.stderr)
        return 1
    for result in results:
        print(f"{result['action']:9} {result['service']} {result['detail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
