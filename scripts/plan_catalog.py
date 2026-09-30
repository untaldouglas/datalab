#!/usr/bin/env python3
"""Genera un plan de solo lectura entre manifiestos y OpenMetadata."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from scripts.validate_catalog_manifests import validate_manifest
except ModuleNotFoundError:  # Ejecutado directamente desde scripts/.
    from validate_catalog_manifests import validate_manifest


DEFAULT_API_URL = "http://localhost:8585/api/v1"


def load_manifests(catalog_dir: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(catalog_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: JSON inválido: {error.msg}") from error
        errors = validate_manifest(document, path)
        if errors:
            raise ValueError("\n".join(errors))
        manifests.append(document)
    if not manifests:
        raise ValueError(f"No hay manifiestos JSON en {catalog_dir}")
    return manifests


def _owner_name(service: dict[str, Any]) -> str | None:
    owner = service.get("owner")
    return owner.get("name") if isinstance(owner, dict) else None


def _classification_tags(service: dict[str, Any]) -> set[str]:
    tags = service.get("tags")
    if not isinstance(tags, list):
        return set()
    values = set()
    for tag in tags:
        if isinstance(tag, dict) and isinstance(tag.get("tagFQN"), str):
            values.add(tag["tagFQN"].lower())
    return values


def _has_classification(service: dict[str, Any], classification: str) -> bool:
    normalized = classification.lower()
    return any(tag == normalized or tag.endswith(f".{normalized}") for tag in _classification_tags(service))


def _differences(manifest: dict[str, Any], service: dict[str, Any]) -> list[dict[str, str]]:
    metadata = manifest["metadata"]
    spec = manifest["spec"]
    desired_service = spec["service"]
    differences: list[dict[str, str]] = []
    comparisons = (
        ("serviceType", desired_service["type"], service.get("serviceType"), True),
        ("description", metadata["description"], service.get("description"), False),
        ("owner", metadata["owner"], _owner_name(service), False),
    )
    for field, desired, actual, case_insensitive in comparisons:
        matches = desired.casefold() == actual.casefold() if case_insensitive and isinstance(actual, str) else desired == actual
        if not matches:
            differences.append({"field": field, "desired": str(desired), "actual": str(actual) if actual is not None else "<missing>"})
    classification = spec["governance"]["classification"]
    if not _has_classification(service, classification):
        differences.append({"field": "classification", "desired": classification, "actual": ", ".join(sorted(_classification_tags(service))) or "<missing>"})
    return differences


def build_plan(manifests: list[dict[str, Any]], services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {service.get("name"): service for service in services if isinstance(service.get("name"), str)}
    plan: list[dict[str, Any]] = []
    for manifest in manifests:
        metadata = manifest["metadata"]
        desired_service = manifest["spec"]["service"]
        service = by_name.get(desired_service["name"])
        if service is None:
            plan.append({"manifest": metadata["name"], "service": desired_service["name"], "action": "CREATE", "differences": []})
            continue
        differences = _differences(manifest, service)
        plan.append({"manifest": metadata["name"], "service": desired_service["name"], "action": "UPDATE" if differences else "NO_CHANGE", "differences": differences})
    return plan


def fetch_database_services(api_url: str, token: str) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        params = {"limit": "100", "fields": "owner,description,tags"}
        if after:
            params["after"] = after
        request = Request(
            f"{api_url.rstrip('/')}/services/databaseServices?{urlencode(params)}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=15) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"OpenMetadata respondió HTTP {error.code} al consultar database services") from error
        except URLError as error:
            raise RuntimeError(f"No se pudo conectar con OpenMetadata: {error.reason}") from error
        data = payload.get("data")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise RuntimeError("OpenMetadata devolvió una lista de servicios inválida")
        services.extend(data)
        after = payload.get("paging", {}).get("after") if isinstance(payload.get("paging"), dict) else None
        if not after:
            return services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=Path("catalog/sources"))
    parser.add_argument("--api-url", default=os.environ.get("OPENMETADATA_API_URL", DEFAULT_API_URL))
    parser.add_argument("--token", default=os.environ.get("OPENMETADATA_JWT_TOKEN"), help="JWT de OpenMetadata; también puede definirse en OPENMETADATA_JWT_TOKEN")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not args.token:
        parser.error("se requiere --token o OPENMETADATA_JWT_TOKEN; el planificador no obtiene ni almacena credenciales")
    try:
        plan = build_plan(load_manifests(args.catalog_dir), fetch_database_services(args.api_url, args.token))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"metadata-plan: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        for entry in plan:
            print(f"{entry['action']:9} {entry['service']} ({entry['manifest']})")
            for difference in entry["differences"]:
                print(f"  - {difference['field']}: catálogo={difference['actual']}; declarado={difference['desired']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
