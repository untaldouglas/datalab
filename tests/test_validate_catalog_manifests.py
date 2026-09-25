import copy
import json
import unittest
from pathlib import Path

from scripts.validate_catalog_manifests import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "catalog" / "sources" / "moodle-postgres.json"
CUSTOM_MANIFEST = ROOT / "catalog" / "sources" / "dremio-federation.json"


class CatalogManifestValidationTest(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_reference_manifest_is_valid(self):
        self.assertEqual([], validate_manifest(self.document, MANIFEST))

    def test_plaintext_password_is_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["access"]["password"] = "not-allowed"
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("campo sensible prohibido" in error for error in errors))

    def test_api_key_and_unknown_access_field_are_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["access"]["apiKey"] = "not-allowed"
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("campo sensible prohibido" in error for error in errors))
        self.assertTrue(any("campos no permitidos" in error for error in errors))

    def test_unknown_service_field_and_type_are_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["service"]["host"] = "postgres-source"
        invalid["spec"]["service"]["type"] = "Unsupported"
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("campos no permitidos" in error for error in errors))
        self.assertTrue(any("tipo soportado" in error for error in errors))

    def test_invalid_cron_is_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["ingestion"]["metadata"]["schedule"] = "99 99 99 99 99"
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("cron válido" in error for error in errors))

    def test_invalid_value_types_return_errors_without_exception(self):
        invalid = copy.deepcopy(self.document)
        invalid["metadata"]["name"] = 3
        invalid["metadata"]["description"] = 3
        invalid["spec"]["ingestion"]["profiler"] = []
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("metadata.name" in error for error in errors))
        self.assertTrue(any("metadata.description" in error for error in errors))
        self.assertTrue(any("spec.ingestion.profiler" in error for error in errors))

    def test_multiline_credentials_reference_is_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["access"]["credentialsRef"] = "airflow-secret://openmetadata/reader\npassword=bad"
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("credentialsRef" in error for error in errors))

    def test_sampling_is_rejected(self):
        invalid = copy.deepcopy(self.document)
        invalid["spec"]["ingestion"]["profiler"]["generateSampleData"] = True
        errors = validate_manifest(invalid, MANIFEST)
        self.assertTrue(any("generateSampleData" in error for error in errors))

    def test_custom_reference_manifest_is_valid(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual([], validate_manifest(document, CUSTOM_MANIFEST))

    def test_custom_source_rejects_invented_operations(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(document)
        invalid["spec"]["operations"].append(
            {"name": "profiler", "trigger": "scheduled", "schedule": "0 3 * * *", "timezone": "America/El_Salvador", "implementation": "custom-airflow"}
        )
        errors = validate_manifest(invalid, CUSTOM_MANIFEST)
        self.assertTrue(any("operación soportada" in error for error in errors))

    def test_custom_scheduled_operation_requires_schedule_and_timezone(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(document)
        invalid["spec"]["operations"][1].pop("schedule")
        invalid["spec"]["operations"][1].pop("timezone")
        errors = validate_manifest(invalid, CUSTOM_MANIFEST)
        self.assertTrue(any("schedule debe ser cron válido" in error for error in errors))
        self.assertTrue(any("timezone debe ser America/El_Salvador" in error for error in errors))

    def test_custom_on_demand_operation_rejects_schedule(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(document)
        invalid["spec"]["operations"][0]["schedule"] = "0 0 * * *"
        errors = validate_manifest(invalid, CUSTOM_MANIFEST)
        self.assertTrue(any("on-demand no debe declarar" in error for error in errors))

    def test_custom_source_rejects_drift_from_current_capabilities_and_bootstrap(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(document)
        invalid["spec"]["capabilities"]["profiler"] = True
        invalid["spec"]["operations"][0]["implementation"] = "custom-airflow"
        errors = validate_manifest(invalid, CUSTOM_MANIFEST)
        self.assertTrue(any("capacidades actuales" in error for error in errors))
        self.assertTrue(any("operación personalizada soportada" in error for error in errors))

    def test_custom_source_requires_all_six_capabilities(self):
        document = json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        invalid = copy.deepcopy(document)
        invalid["spec"]["capabilities"].pop("usage")
        errors = validate_manifest(invalid, CUSTOM_MANIFEST)
        self.assertTrue(any("seis capacidades booleanas" in error for error in errors))
