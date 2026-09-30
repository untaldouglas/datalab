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
    return {key: owner[key] for key in ("id", "type", "name") if key in owner}


def apply_manifests(manifests: list[dict[str, Any]], api_url: str, token: str) -> list[dict[str, str]]:
    ensure_governance_tags(api_url, token)
    services = {service.get("name"): service for service in fetch_database_services(api_url, token) if isinstance(service.get("name"), str)}
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
