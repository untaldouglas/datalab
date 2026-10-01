import unittest
from unittest.mock import patch

from scripts import apply_catalog


MANIFEST_SIS = {
    "apiVersion": "catalog.university.local/v1alpha1",
    "kind": "CatalogSource",
    "metadata": {"name": "sis-mssql", "owner": "admin", "description": "desc"},
    "spec": {
        "environment": "local",
        "service": {"name": "SIS_MSSQL", "type": "MSSQL", "database": "sis_db", "includeSchemas": ["sis"]},
        "ingestion": {
            "metadata": {"enabled": True},
            "quality": {"enabled": True, "schedule": "0 4 * * *", "timezone": "America/El_Salvador", "initialTests": ["row_count_positive"]},
        },
        "governance": {"defaultOwner": "admin", "classification": "restricted"},
        "tables": [{"database": "sis_db", "schema": "sis", "name": "academic_registrations", "description": "desc"}],
    },
}

MANIFEST_ERP = {
    "apiVersion": "catalog.university.local/v1alpha1",
    "kind": "CatalogSource",
    "metadata": {"name": "erp-mssql", "owner": "admin", "description": "desc"},
    "spec": {
        "environment": "local",
        "service": {"name": "ERPNext_Postgres", "type": "Postgres", "database": "erpnext_db", "includeSchemas": ["erp"]},
        "ingestion": {
            "metadata": {"enabled": True},
            "quality": {"enabled": True, "schedule": "0 4 * * *", "timezone": "America/El_Salvador", "initialTests": ["row_count_positive"]},
        },
        "governance": {"defaultOwner": "admin", "classification": "restricted"},
        "tables": [{"database": "erpnext_db", "schema": "erp", "name": "registration_payments", "description": "desc"}],
    },
}

MANIFEST_SIN_TABLAS = {
    "apiVersion": "catalog.university.local/v1alpha1",
    "kind": "CatalogSource",
    "metadata": {"name": "moodle-postgres", "owner": "admin", "description": "desc"},
    "spec": {
        "environment": "local",
        "service": {"name": "Moodle_Postgres", "type": "Postgres", "database": "moodle_db", "includeSchemas": ["moodle"]},
        "ingestion": {
            "metadata": {"enabled": True},
            "quality": {"enabled": True, "schedule": "0 4 * * *", "timezone": "America/El_Salvador", "initialTests": ["row_count_positive"]},
        },
        "governance": {"defaultOwner": "admin", "classification": "restricted"},
    },
}

MANIFEST_SIN_CALIDAD = {
    "apiVersion": "catalog.university.local/v1alpha1",
    "kind": "CatalogSource",
    "metadata": {"name": "dremio-federation", "owner": "admin", "description": "desc"},
    "spec": {
        "environment": "local",
        "service": {"name": "Dremio_Federation", "type": "Dremio", "database": "Dremio", "includeSchemas": ["Dremio"]},
        "governance": {"defaultOwner": "admin", "classification": "internal"},
    },
}

SERVICES = {
    "SIS_MSSQL": {"id": "svc-sis", "name": "SIS_MSSQL"},
    "ERPNext_Postgres": {"id": "svc-erpnext", "name": "ERPNext_Postgres"},
    "Moodle_Postgres": {"id": "svc-moodle", "name": "Moodle_Postgres"},
}


class ApplyQualityControlTest(unittest.TestCase):
    def test_quality_tables_exactly_two_declared_sources(self):
        pairs = apply_catalog.quality_tables([MANIFEST_SIS, MANIFEST_ERP, MANIFEST_SIN_TABLAS, MANIFEST_SIN_CALIDAD])

        self.assertEqual(
            [("SIS_MSSQL", "academic_registrations"), ("ERPNext_Postgres", "registration_payments")],
            [(service["name"], table["name"]) for _manifest, service, table in pairs],
        )

    def test_ensure_quality_control_creates_suite_case_and_pipeline(self):
        created: list[tuple[str, str]] = []

        def fake_request(method, url, token, payload=None, content_type="application/json", not_found_ok=False):
            if isinstance(url, str) and url.endswith("/services/ingestionPipelines?limit=200"):
                return {"data": []}
            if payload is None:
                return None
            if method == "PUT":
                created.append((url, str(payload["name"])))
                return dict(payload)
            if method == "POST":
                created.append((url, str(payload["name"])))
            return None

        with patch.object(apply_catalog, "request_json", side_effect=fake_request):
            results = apply_catalog.ensure_quality_control([MANIFEST_SIS, MANIFEST_ERP], "http://api", "token", SERVICES)

        self.assertEqual(["UPDATED", "UPDATED"], [result["action"] for result in results])
        self.assertIn(("http://api/dataQuality/testSuites/executable", "SIS_MSSQL.sis_db.sis.academic_registrations.TestSuite"), created)
        self.assertIn(("http://api/dataQuality/testCases", "row_count_positive"), created)
        self.assertIn(("http://api/services/ingestionPipelines", "SIS_MSSQL_academic_registrations_dq"), created)
        self.assertIn(("http://api/services/ingestionPipelines", "ERPNext_Postgres_registration_payments_dq"), created)

    def test_ensure_quality_control_is_idempotent_when_everything_exists(self):
        def fake_request(method, url, token, payload=None, content_type="application/json", not_found_ok=False):
            if isinstance(url, str) and url.endswith("/services/ingestionPipelines?limit=200"):
                return {"data": [{"name": "SIS_MSSQL_academic_registrations_dq", "service": {"name": "SIS_MSSQL"}}, {"name": "ERPNext_Postgres_registration_payments_dq", "service": {"name": "ERPNext_Postgres"}}]}
            return {"id": "x"}

        with patch.object(apply_catalog, "request_json", side_effect=fake_request):
            results = apply_catalog.ensure_quality_control([MANIFEST_SIS, MANIFEST_ERP], "http://api", "token", SERVICES)

        self.assertEqual(["NO_CHANGE", "NO_CHANGE"], [result["action"] for result in results])

    def test_ensure_quality_control_blocks_when_service_is_absent(self):
        def fake_request(method, url, token, payload=None, content_type="application/json", not_found_ok=False):
            if isinstance(url, str) and url.endswith("/services/ingestionPipelines?limit=200"):
                return {"data": []}
            return None
        with patch.object(apply_catalog, "request_json", side_effect=fake_request):
            results = apply_catalog.ensure_quality_control([MANIFEST_SIS], "http://api", "token", {"Moodle_Postgres": {"id": "svc"}})

        self.assertEqual("BLOCKED", results[0]["action"])


if __name__ == "__main__":
    unittest.main()
