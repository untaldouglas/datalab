import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from scripts.plan_catalog import build_plan, fetch_database_services, load_manifests


ROOT = Path(__file__).resolve().parents[1]


class CatalogPlanTest(unittest.TestCase):
    def test_matching_service_is_reported_without_changes(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]
        service = {
            "name": manifest["spec"]["service"]["name"],
            "serviceType": manifest["spec"]["service"]["type"],
            "description": manifest["metadata"]["description"],
            "owner": {"name": manifest["metadata"]["owner"]},
            "tags": [{"tagFQN": manifest["spec"]["governance"]["classification"]}],
        }

        plan = build_plan([manifest], [service])

        self.assertEqual(
            [{"manifest": manifest["metadata"]["name"], "service": service["name"], "action": "NO_CHANGE", "differences": []}],
            plan,
        )

    def test_missing_service_is_reported_as_create(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]

        plan = build_plan([manifest], [])

        self.assertEqual("CREATE", plan[0]["action"])
        self.assertEqual([], plan[0]["differences"])

    def test_drift_in_owner_description_type_and_classification_is_reported(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]
        service = {
            "name": manifest["spec"]["service"]["name"],
            "serviceType": "Postgres",
            "description": "Otra descripción",
            "owner": {"name": "other-owner"},
            "tags": [{"tagFQN": "PII.Confidential"}],
        }

        plan = build_plan([manifest], [service])

        self.assertEqual("UPDATE", plan[0]["action"])
        self.assertEqual(
            ["serviceType", "description", "owner", "classification"],
            [difference["field"] for difference in plan[0]["differences"]],
        )

    def test_service_type_comparison_ignores_casing_used_by_openmetadata(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[1]
        service = {
            "name": manifest["spec"]["service"]["name"],
            "serviceType": "Mssql",
            "description": manifest["metadata"]["description"],
            "owner": {"name": manifest["metadata"]["owner"]},
            "tags": [{"tagFQN": manifest["spec"]["governance"]["classification"]}],
        }

        plan = build_plan([manifest], [service])

        self.assertEqual("NO_CHANGE", plan[0]["action"])

    def test_fetches_services_with_get_and_bearer_token(self):
        response = BytesIO(b'{"data": [{"name": "Moodle_Postgres"}], "paging": {}}')

        with patch("scripts.plan_catalog.urlopen", return_value=response) as open_url:
            services = fetch_database_services("http://catalog.test/api/v1", "temporary-token")

        self.assertEqual([{"name": "Moodle_Postgres"}], services)
        request = open_url.call_args.args[0]
        self.assertEqual("GET", request.method)
        self.assertEqual("Bearer temporary-token", request.get_header("Authorization"))
        self.assertIn("services/databaseServices?", request.full_url)
