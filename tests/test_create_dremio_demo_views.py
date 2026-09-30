import unittest
from unittest.mock import Mock, patch

from scripts.create_dremio_demo_views import VIEW_SQL, submit_and_wait


class DremioDemoViewsTest(unittest.TestCase):
    def test_views_preserve_the_approved_business_rules(self):
        eligibility = VIEW_SQL["Eligible_Student_Activity"]
        events = VIEW_SQL["Academic_Activity_Events"]
        academic_summary = VIEW_SQL["Rectoral_Academic_Summary"]

        self.assertIn("p.payment_status IN ('paid', 'partial')", eligibility)
        self.assertIn("r.registration_status = 'vigente'", eligibility)
        self.assertIn("moodle_user.role_name = 'student'", events)
        self.assertIn("submission.submission_status = 'submitted'", events)
        self.assertIn("attempt.attempt_state = 'finished'", events)
        self.assertIn("event.event_date > DATE_SUB(cutoff.reporting_cutoff, 28)", academic_summary)
        self.assertIn("event.event_date <= cutoff.reporting_cutoff", academic_summary)

    @patch("scripts.create_dremio_demo_views.time.sleep")
    def test_submit_and_wait_returns_after_dremio_completes(self, sleep):
        session = Mock()
        session.post.return_value.json.return_value = {"id": "job-1"}
        session.get.side_effect = [
            Mock(json=lambda: {"jobState": "RUNNING"}),
            Mock(json=lambda: {"jobState": "COMPLETED"}),
        ]

        submit_and_wait(session, "http://dremio.test", "SELECT 1")

        self.assertEqual(2, session.get.call_count)
        sleep.assert_called_once_with(1)

    def test_submit_and_wait_surfaces_a_failed_dremio_job(self):
        session = Mock()
        session.post.return_value.json.return_value = {"id": "job-1"}
        session.get.return_value.json.return_value = {"jobState": "FAILED", "errorMessage": "bad SQL"}

        with self.assertRaisesRegex(RuntimeError, "bad SQL"):
            submit_and_wait(session, "http://dremio.test", "SELECT 1")
