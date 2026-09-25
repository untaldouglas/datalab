import copy
import json
import unittest
from pathlib import Path

from scripts.validate_catalog_manifests import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "catalog" / "sources" / "moodle-postgres.json"


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
