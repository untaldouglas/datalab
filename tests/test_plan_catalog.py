import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.apply_catalog import build_service_patch, managed_tag_fqn, request_json, service_type_matches
from scripts.plan_catalog import build_plan, fetch_database_services, load_manifests


ROOT = Path(__file__).resolve().parents[1]


class CatalogPlanTest(unittest.TestCase):
    def test_apply_blocks_service_type_drift_except_for_casing(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[1]

        self.assertTrue(service_type_matches(manifest, {"serviceType": "Mssql"}))
        self.assertFalse(service_type_matches(manifest, {"serviceType": "Postgres"}))

    def test_apply_request_fails_when_a_patch_target_is_missing(self):
        error = HTTPError("http://catalog.test/service", 404, "Not found", {}, BytesIO())

        with patch("scripts.apply_catalog.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
                request_json("PATCH", "http://catalog.test/service", "temporary-token", [])

    def test_apply_patch_updates_description_and_adds_managed_classification(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]
        service = {
            "description": "Descripción anterior",
            "owner": {"id": "owner-id", "name": "admin"},
            "tags": [{"tagFQN": "PII.Sensitive", "labelType": "Manual", "state": "Confirmed"}],
        }

        patch = build_service_patch(manifest, service, {"id": "owner-id", "type": "user", "name": "admin"})

        self.assertEqual(
            [
                {"op": "replace", "path": "/description", "value": manifest["metadata"]["description"]},
                {
                    "op": "replace",
                    "path": "/tags",
                    "value": [
                        {"tagFQN": "PII.Sensitive", "labelType": "Manual", "state": "Confirmed"},
                        {"tagFQN": managed_tag_fqn(manifest), "labelType": "Manual", "state": "Confirmed"},
                    ],
                },
            ],
            patch,
        )

    def test_apply_patch_replaces_a_different_owner(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]
        service = {"description": manifest["metadata"]["description"], "owner": {"name": "legacy"}, "tags": [{"tagFQN": managed_tag_fqn(manifest)}]}
        owner = {"id": "owner-id", "type": "user", "name": "admin"}

        patch = build_service_patch(manifest, service, owner)

        self.assertEqual([{"op": "replace", "path": "/owner", "value": owner}], patch)

    def test_apply_replaces_another_tag_from_the_managed_classification(self):
        manifest = load_manifests(ROOT / "catalog" / "sources")[0]
        service = {
            "description": manifest["metadata"]["description"],
            "owner": {"id": "owner-id", "name": "admin"},
            "tags": [
                {"tagFQN": "PII.Sensitive", "labelType": "Manual", "state": "Confirmed"},
                {"tagFQN": "UniversityClassification.Confidential", "labelType": "Manual", "state": "Confirmed"},
                {"tagFQN": managed_tag_fqn(manifest), "labelType": "Manual", "state": "Confirmed"},
            ],
        }

        patch = build_service_patch(manifest, service, {"id": "owner-id", "type": "user", "name": "admin"})

        self.assertEqual(["PII.Sensitive", managed_tag_fqn(manifest)], [tag["tagFQN"] for tag in patch[0]["value"]])

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
