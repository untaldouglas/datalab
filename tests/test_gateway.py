import unittest

from gateway.app import METRICS, build_metric_query


class GatewayQueryTest(unittest.TestCase):
    def test_academic_query_accepts_only_approved_business_filter(self):
        query = build_metric_query("academic", {"faculty": ["Ingeniería"]})

        self.assertIn('"Rectoral_Academic_Summary"', query)
        self.assertIn("faculty = 'Ingeniería'", query)

    def test_gateway_rejects_sql_and_unapproved_filters(self):
        with self.assertRaisesRegex(ValueError, "Filtro no autorizado"):
            build_metric_query("academic", {"sql": ["SELECT * FROM Student_360"]})
        with self.assertRaisesRegex(ValueError, "Valor de filtro no autorizado"):
            build_metric_query("financial", {"status": ["paid' OR 1=1 --"]})

    def test_gateway_rejects_an_unknown_metric(self):
        with self.assertRaisesRegex(ValueError, "Métrica no autorizada"):
            build_metric_query("students", {})

    def test_only_the_two_approved_aggregate_views_are_exposed(self):
        self.assertEqual({"academic", "financial"}, set(METRICS))
        self.assertEqual('"Gold_Rectoria"."Rectoral_Academic_Summary"', METRICS["academic"]["view"])
        self.assertEqual('"Gold_Rectoria"."Rectoral_Financial_Summary"', METRICS["financial"]["view"])
