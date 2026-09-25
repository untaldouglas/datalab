#!/usr/bin/env python3
"""Valida los manifiestos Metadata-as-Code sin dependencias externas."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT_REQUIRED = {"apiVersion", "kind", "metadata", "spec"}
CUSTOM_API_VERSION = "catalog.university.local/custom-v1alpha1"
FORBIDDEN_KEY = re.compile(
    r"(?:password|passwd|token|private.?key|secret|api.?key|authorization|connection.?string|credential)s?$",
    re.IGNORECASE,
)
ALLOWED = {
    "metadata": {"name", "owner", "description"},
    "spec": {"environment", "service", "access", "ingestion", "governance"},
    "service": {"name", "type", "database", "includeSchemas"},
    "access": {"credentialsRef", "mode"},
    "ingestion": {"metadata", "profiler", "quality"},
    "scheduledPipeline": {"enabled", "schedule", "timezone"},
    "profiler": {"enabled", "schedule", "timezone", "generateSampleData"},
    "quality": {"enabled", "schedule", "timezone", "initialTests"},
    "governance": {"defaultOwner", "classification"},
    "customSpec": {"environment", "service", "access", "capabilities", "operations", "governance"},
    "capabilities": {"nativeMetadataIngestion", "metadataBootstrap", "profiler", "quality", "lineage", "usage"},
    "operation": {"name", "trigger", "schedule", "timezone", "implementation"},
}
SERVICE_TYPES = {"Postgres", "MSSQL", "MySQL", "Oracle", "CustomDatabase"}
CRON_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
CREDENTIALS_REF = re.compile(r"(?:openbao|sops|airflow-secret)://[^/\s]+/[^\s]+")


def fail(path: Path, message: str) -> str:
    return f"{path}: {message}"


def has_forbidden_secret(value: Any, location: str = "") -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}" if location else key
            if FORBIDDEN_KEY.search(key):
                return f"contiene el campo sensible prohibido '{child_location}'"
            found = has_forbidden_secret(child, child_location)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = has_forbidden_secret(child, f"{location}[{index}]")
            if found:
                return found
    return None


def reject_unknown_fields(value: Any, allowed: set[str], location: str, path: Path) -> list[str]:
    if not isinstance(value, dict):
        return [fail(path, f"{location} debe ser un objeto")]
    unknown = set(value) - allowed
    if not unknown:
        return []
    return [fail(path, f"{location} contiene campos no permitidos: {', '.join(sorted(unknown))}")]


def cron_part_is_valid(part: str, lower: int, upper: int) -> bool:
    for item in part.split(","):
        base, *step_parts = item.split("/")
        if len(step_parts) > 1 or (step_parts and (not step_parts[0].isdigit() or int(step_parts[0]) < 1)):
            return False
        if base == "*":
            continue
        if "-" in base:
            bounds = base.split("-")
            if len(bounds) != 2 or not all(bound.isdigit() for bound in bounds):
                return False
            start, end = map(int, bounds)
            if not (lower <= start <= end <= upper):
                return False
            continue
        if not base.isdigit() or not lower <= int(base) <= upper:
            return False
    return True


def cron_is_valid(schedule: str) -> bool:
    fields = schedule.split()
    return len(fields) == 5 and all(
        cron_part_is_valid(field, lower, upper)
        for field, (lower, upper) in zip(fields, CRON_RANGES, strict=True)
    )


def validate_metadata(metadata: Any, path: Path) -> list[str]:
    if not isinstance(metadata, dict):
        return [fail(path, "metadata debe ser un objeto")]
    errors = reject_unknown_fields(metadata, ALLOWED["metadata"], "metadata", path)
    for field in ("name", "owner", "description"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            errors.append(fail(path, f"metadata.{field} es obligatorio"))
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(description, str) or len(description) < 20:
        errors.append(fail(path, "metadata.description debe tener al menos 20 caracteres"))
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", name):
        errors.append(fail(path, "metadata.name debe usar minúsculas, números o guiones"))
    return errors


def validate_common_service_access_governance(spec: dict[str, Any], metadata: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    service = spec.get("service") if isinstance(spec.get("service"), dict) else {}
    access = spec.get("access") if isinstance(spec.get("access"), dict) else {}
    governance = spec.get("governance") if isinstance(spec.get("governance"), dict) else {}
    errors.extend(reject_unknown_fields(service, ALLOWED["service"], "spec.service", path))
    errors.extend(reject_unknown_fields(access, ALLOWED["access"], "spec.access", path))
    errors.extend(reject_unknown_fields(governance, ALLOWED["governance"], "spec.governance", path))
    if spec.get("environment") not in {"local", "development", "test", "staging", "production"}:
        errors.append(fail(path, "spec.environment no es un ambiente permitido"))
    for field in ("name", "type", "database"):
        if not isinstance(service.get(field), str) or not service[field].strip():
            errors.append(fail(path, f"spec.service.{field} es obligatorio"))
    if service.get("type") not in SERVICE_TYPES:
        errors.append(fail(path, "spec.service.type no es un tipo soportado"))
    schemas = service.get("includeSchemas")
    if not isinstance(schemas, list) or not schemas or not all(isinstance(item, str) and item for item in schemas):
        errors.append(fail(path, "spec.service.includeSchemas debe contener al menos un esquema"))
    if access.get("mode") != "read-only":
        errors.append(fail(path, "spec.access.mode debe ser read-only"))
    if not isinstance(access.get("credentialsRef"), str) or not CREDENTIALS_REF.fullmatch(access["credentialsRef"]):
        errors.append(fail(path, "spec.access.credentialsRef debe ser una referencia de secreto admitida"))
    if governance.get("defaultOwner") != metadata.get("owner"):
        errors.append(fail(path, "governance.defaultOwner debe coincidir con metadata.owner"))
    if governance.get("classification") not in {"internal", "confidential", "restricted"}:
        errors.append(fail(path, "spec.governance.classification no es válida"))
    return errors


def validate_custom_manifest(document: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    metadata = document["metadata"]
    spec = document["spec"]
    if not isinstance(metadata, dict) or not isinstance(spec, dict):
        return [fail(path, "metadata y spec deben ser objetos")]
    errors.extend(validate_metadata(metadata, path))
    errors.extend(reject_unknown_fields(spec, ALLOWED["customSpec"], "spec", path))
    errors.extend(validate_common_service_access_governance(spec, metadata, path))
    service = spec.get("service") if isinstance(spec.get("service"), dict) else {}
    if service.get("type") != "CustomDatabase":
        errors.append(fail(path, "una fuente personalizada debe usar service.type CustomDatabase"))

    capabilities = spec.get("capabilities") if isinstance(spec.get("capabilities"), dict) else {}
    errors.extend(reject_unknown_fields(capabilities, ALLOWED["capabilities"], "spec.capabilities", path))
    required_capabilities = ALLOWED["capabilities"]
    if set(capabilities) != required_capabilities or not all(isinstance(capabilities.get(name), bool) for name in required_capabilities):
        errors.append(fail(path, "spec.capabilities debe declarar seis capacidades booleanas"))

    operations = spec.get("operations")
    if not isinstance(operations, list) or not operations:
        errors.append(fail(path, "spec.operations debe contener al menos una operación"))
        return errors + ([fail(path, has_forbidden_secret(document))] if has_forbidden_secret(document) else [])
    names: set[str] = set()
    for index, operation in enumerate(operations):
        location = f"spec.operations[{index}]"
        errors.extend(reject_unknown_fields(operation, ALLOWED["operation"], location, path))
        if not isinstance(operation, dict):
            continue
        name = operation.get("name")
        trigger = operation.get("trigger")
        if name not in {"bootstrap", "lineage", "usage"}:
            errors.append(fail(path, f"{location}.name no es una operación soportada"))
        elif name in names:
            errors.append(fail(path, f"{location}.name está duplicada"))
        else:
            names.add(name)
        expected_operation = {
            "bootstrap": ("on-demand", "custom-script"),
            "lineage": ("scheduled", "custom-airflow"),
            "usage": ("scheduled", "custom-airflow"),
        }.get(name)
        if expected_operation and (trigger, operation.get("implementation")) != expected_operation:
            errors.append(fail(path, f"{location} no representa la operación personalizada soportada"))
        if trigger == "scheduled":
            if not isinstance(operation.get("schedule"), str) or not cron_is_valid(operation["schedule"]):
                errors.append(fail(path, f"{location}.schedule debe ser cron válido de cinco campos"))
            if operation.get("timezone") != "America/El_Salvador":
                errors.append(fail(path, f"{location}.timezone debe ser America/El_Salvador"))
        elif trigger == "on-demand":
            if "schedule" in operation or "timezone" in operation:
                errors.append(fail(path, f"{location} on-demand no debe declarar schedule ni timezone"))
        else:
            errors.append(fail(path, f"{location}.trigger debe ser scheduled u on-demand"))
    if not {"bootstrap", "lineage", "usage"}.issubset(names):
        errors.append(fail(path, "spec.operations debe declarar bootstrap, lineage y usage"))
    expected_capabilities = {
        "nativeMetadataIngestion": False, "metadataBootstrap": True, "profiler": False,
        "quality": False, "lineage": True, "usage": True,
    }
    if capabilities != expected_capabilities:
        errors.append(fail(path, "spec.capabilities no representa las capacidades actuales de la integración personalizada"))
    forbidden = has_forbidden_secret(document)
    if forbidden:
        errors.append(fail(path, forbidden))
    return errors


def validate_manifest(document: Any, path: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return [fail(path, "el manifiesto debe ser un objeto JSON")]

    unknown = set(document) - ROOT_REQUIRED
    missing = ROOT_REQUIRED - set(document)
    if unknown:
        errors.append(fail(path, f"campos de nivel superior no permitidos: {', '.join(sorted(unknown))}"))
    if missing:
        errors.append(fail(path, f"faltan campos requeridos: {', '.join(sorted(missing))}"))
        return errors
    if document["apiVersion"] == CUSTOM_API_VERSION and document["kind"] == "CustomCatalogSource":
        return errors + validate_custom_manifest(document, path)
    if document["apiVersion"] != "catalog.university.local/v1alpha1":
        errors.append(fail(path, "apiVersion no soportada"))
    if document["kind"] != "CatalogSource":
        errors.append(fail(path, "kind debe ser CatalogSource"))

    metadata = document["metadata"]
    spec = document["spec"]
    if not isinstance(metadata, dict) or not isinstance(spec, dict):
        return errors + [fail(path, "metadata y spec deben ser objetos")]
    errors.extend(validate_metadata(metadata, path))
    errors.extend(reject_unknown_fields(spec, ALLOWED["spec"], "spec", path))

    service = spec.get("service") if isinstance(spec.get("service"), dict) else {}
    access = spec.get("access") if isinstance(spec.get("access"), dict) else {}
    governance = spec.get("governance") if isinstance(spec.get("governance"), dict) else {}
    ingestion = spec.get("ingestion") if isinstance(spec.get("ingestion"), dict) else {}
    errors.extend(reject_unknown_fields(ingestion, ALLOWED["ingestion"], "spec.ingestion", path))
    errors.extend(validate_common_service_access_governance(spec, metadata, path))

    for pipeline in ("metadata", "profiler", "quality"):
        config = ingestion.get(pipeline) if isinstance(ingestion.get(pipeline), dict) else {}
        allowed = ALLOWED[pipeline] if pipeline in {"profiler", "quality"} else ALLOWED["scheduledPipeline"]
        errors.extend(reject_unknown_fields(config, allowed, f"spec.ingestion.{pipeline}", path))
        if config.get("enabled") is not True:
            errors.append(fail(path, f"spec.ingestion.{pipeline}.enabled debe ser true"))
        if not isinstance(config.get("schedule"), str) or not cron_is_valid(config["schedule"]):
            errors.append(fail(path, f"spec.ingestion.{pipeline}.schedule debe ser cron válido de cinco campos"))
        if config.get("timezone") != "America/El_Salvador":
            errors.append(fail(path, f"spec.ingestion.{pipeline}.timezone debe ser America/El_Salvador"))
    profiler = ingestion.get("profiler") if isinstance(ingestion.get("profiler"), dict) else {}
    quality = ingestion.get("quality") if isinstance(ingestion.get("quality"), dict) else {}
    if profiler.get("generateSampleData") is not False:
        errors.append(fail(path, "el profiler debe deshabilitar generateSampleData"))
    tests = quality.get("initialTests")
    if not isinstance(tests, list) or not tests or not all(isinstance(item, str) and item for item in tests):
        errors.append(fail(path, "quality.initialTests debe contener al menos una prueba"))

    forbidden = has_forbidden_secret(document)
    if forbidden:
        errors.append(fail(path, forbidden))
    return errors


def main(argv: list[str]) -> int:
    directory = Path(argv[1]) if len(argv) == 2 else Path("catalog/sources")
    manifests = sorted(directory.glob("*.json"))
    if not manifests:
        print(f"No se encontraron manifiestos JSON en {directory}", file=sys.stderr)
        return 1
    errors: list[str] = []
    for manifest in manifests:
        try:
            document = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(fail(manifest, f"JSON inválido: {exc.msg}"))
            continue
        errors.extend(validate_manifest(document, manifest))
    if errors:
        print("Validación Metadata-as-Code falló:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Metadata-as-Code válido: {len(manifests)} manifiesto(s) en {directory}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
