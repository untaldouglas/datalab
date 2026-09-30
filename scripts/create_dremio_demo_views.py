#!/usr/bin/env python3
"""Crea de forma idempotente los espacios medallion y las vistas Dremio aprobadas para la demo.

Capas (ADR 0003):
- Bronce: las fuentes registradas en Dremio (`Moodle_Postgres`, `SIS_MSSQL`,
  `ERPNext_Postgres`, `MinIO_Lakehouse`); no se crean objetos nuevos.
- Plata: espacio `Silver` con reglas de negocio reutilizables.
- Oro: espacios `Gold_Rectoria`, `Gold_Decanatos`, `Gold_VR_Financiera` con
  agregados de consumo por audiencia.
"""
import os
import time
import urllib.parse

import requests

SPACES = ["Silver", "Gold_Rectoria", "Gold_Decanatos", "Gold_VR_Financiera"]

LEGACY_VIEWS = [
    "Eligible_Student_Activity",
    "Demo_Reporting_Cutoff",
    "Academic_Activity_Events",
    "Rectoral_Academic_Summary",
    "Rectoral_Financial_Summary",
]

VIEW_SQL = {
    "Silver.Eligible_Student_Activity": '''CREATE OR REPLACE VIEW "Silver"."Eligible_Student_Activity" AS
SELECT r.student_id, s.full_name, r.academic_term, s.academic_program,
  CASE WHEN s.academic_program = 'Administración' THEN 'Administración'
       WHEN s.academic_program = 'Ingeniería de Datos' THEN 'Ingeniería'
       ELSE 'Economía' END AS faculty,
  e.course_code, p.payment_status,
  CASE WHEN p.payment_status = 'partial' THEN 'temporal' ELSE 'eligible' END AS eligibility_status
FROM "SIS_MSSQL".sis.academic_registrations r
JOIN "SIS_MSSQL".sis.students s ON s.student_id = r.student_id
JOIN "SIS_MSSQL".sis.enrollments e ON e.student_id = r.student_id AND e.academic_term = r.academic_term
JOIN "ERPNext_Postgres".erp.registration_payments p ON p.registration_id = r.registration_id AND p.student_id = r.student_id AND p.academic_term = r.academic_term
WHERE r.registration_status = 'vigente' AND e.enrollment_status = 'enrolled' AND p.payment_status IN ('paid', 'partial')''',
    "Silver.Demo_Reporting_Cutoff": '''CREATE OR REPLACE VIEW "Silver"."Demo_Reporting_Cutoff" AS
SELECT DATE '2026-03-31' AS reporting_cutoff''',
    "Silver.Academic_Activity_Events": '''CREATE OR REPLACE VIEW "Silver"."Academic_Activity_Events" AS
SELECT eligible.student_id, eligible.academic_term, eligible.faculty, eligible.academic_program,
  eligible.course_code, 'assignment_submitted' AS activity_type, CAST(submission.submitted_at AS DATE) AS event_date
FROM "Silver"."Eligible_Student_Activity" eligible
JOIN "SIS_MSSQL".sis.students sis_student ON sis_student.student_id = eligible.student_id
JOIN "Moodle_Postgres".moodle.users moodle_user ON moodle_user.email = sis_student.university_email
JOIN "Moodle_Postgres".moodle.assignment_submissions submission ON submission.user_id = moodle_user.user_id
JOIN "Moodle_Postgres".moodle.assignments assignment ON assignment.assignment_id = submission.assignment_id
JOIN "Moodle_Postgres".moodle.courses course ON course.course_id = assignment.course_id AND course.course_code = eligible.course_code
WHERE moodle_user.role_name = 'student' AND submission.submission_status = 'submitted' AND submission.submitted_at IS NOT NULL
UNION ALL
SELECT eligible.student_id, eligible.academic_term, eligible.faculty, eligible.academic_program,
  eligible.course_code, 'quiz_finished' AS activity_type, CAST(attempt.finished_at AS DATE) AS event_date
FROM "Silver"."Eligible_Student_Activity" eligible
JOIN "SIS_MSSQL".sis.students sis_student ON sis_student.student_id = eligible.student_id
JOIN "Moodle_Postgres".moodle.users moodle_user ON moodle_user.email = sis_student.university_email
JOIN "Moodle_Postgres".moodle.quiz_attempts attempt ON attempt.user_id = moodle_user.user_id
JOIN "Moodle_Postgres".moodle.quizzes quiz ON quiz.quiz_id = attempt.quiz_id
JOIN "Moodle_Postgres".moodle.courses course ON course.course_id = quiz.course_id AND course.course_code = eligible.course_code
WHERE moodle_user.role_name = 'student' AND attempt.attempt_state = 'finished' AND attempt.finished_at IS NOT NULL
UNION ALL
SELECT eligible.student_id, eligible.academic_term, eligible.faculty, eligible.academic_program,
  eligible.course_code, 'forum_posted' AS activity_type, CAST(post.posted_at AS DATE) AS event_date
FROM "Silver"."Eligible_Student_Activity" eligible
JOIN "SIS_MSSQL".sis.students sis_student ON sis_student.student_id = eligible.student_id
JOIN "Moodle_Postgres".moodle.users moodle_user ON moodle_user.email = sis_student.university_email
JOIN "Moodle_Postgres".moodle.forum_posts post ON post.user_id = moodle_user.user_id
JOIN "Moodle_Postgres".moodle.courses course ON course.course_id = post.course_id AND course.course_code = eligible.course_code
WHERE moodle_user.role_name = 'student' ''',
    "Gold_Rectoria.Rectoral_Academic_Summary": '''CREATE OR REPLACE VIEW "Gold_Rectoria"."Rectoral_Academic_Summary" AS
WITH participation AS (
  SELECT DISTINCT event.student_id, event.academic_term, event.faculty, event.academic_program, event.course_code
  FROM "Silver"."Academic_Activity_Events" event
  CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
  WHERE event.event_date > DATE_SUB(cutoff.reporting_cutoff, 28) AND event.event_date <= cutoff.reporting_cutoff
)
SELECT eligible.academic_term, eligible.faculty, eligible.academic_program, eligible.course_code,
  cutoff.reporting_cutoff,
  COUNT(DISTINCT eligible.student_id) AS eligible_students,
  COUNT(DISTINCT participation.student_id) AS participating_students,
  COUNT(DISTINCT eligible.student_id) - COUNT(DISTINCT participation.student_id) AS eligible_without_recent_activity,
  CAST(100.0 * COUNT(DISTINCT participation.student_id) / NULLIF(COUNT(DISTINCT eligible.student_id), 0) AS DECIMAL(5,2)) AS participation_pct
FROM "Silver"."Eligible_Student_Activity" eligible
CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
LEFT JOIN participation ON participation.student_id = eligible.student_id AND participation.academic_term = eligible.academic_term AND participation.course_code = eligible.course_code
GROUP BY eligible.academic_term, eligible.faculty, eligible.academic_program, eligible.course_code, cutoff.reporting_cutoff''',
    "Gold_Rectoria.Rectoral_Financial_Summary": '''CREATE OR REPLACE VIEW "Gold_Rectoria"."Rectoral_Financial_Summary" AS
SELECT
  CASE WHEN EXTRACT(MONTH FROM invoice.invoice_date) BETWEEN 1 AND 7
       THEN CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-01')
       ELSE CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-02') END AS academic_semester,
  cutoff.reporting_cutoff, invoice.payment_status,
  COUNT(*) AS invoices,
  SUM(invoice.total_amount) AS billed_amount,
  SUM(invoice.paid_amount) AS paid_amount,
  SUM(invoice.total_amount - invoice.paid_amount) AS outstanding_amount
FROM "ERPNext_Postgres".erp.student_invoices invoice
CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
WHERE invoice.invoice_date <= cutoff.reporting_cutoff
GROUP BY CASE WHEN EXTRACT(MONTH FROM invoice.invoice_date) BETWEEN 1 AND 7
       THEN CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-01')
       ELSE CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-02') END,
  cutoff.reporting_cutoff, invoice.payment_status''',
    "Gold_Decanatos.Decanato_Program_Participation": '''CREATE OR REPLACE VIEW "Gold_Decanatos"."Decanato_Program_Participation" AS
SELECT eligible.faculty, eligible.academic_program, eligible.academic_term,
  cutoff.reporting_cutoff,
  COUNT(DISTINCT eligible.student_id) AS eligible_students,
  COUNT(DISTINCT participation.student_id) AS participating_students,
  COUNT(DISTINCT eligible.student_id) - COUNT(DISTINCT participation.student_id) AS eligible_without_recent_activity,
  CAST(100.0 * COUNT(DISTINCT participation.student_id) / NULLIF(COUNT(DISTINCT eligible.student_id), 0) AS DECIMAL(5,2)) AS participation_pct
FROM "Silver"."Eligible_Student_Activity" eligible
CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
LEFT JOIN (
  SELECT DISTINCT event.student_id, event.academic_term, event.course_code
  FROM "Silver"."Academic_Activity_Events" event
  CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
  WHERE event.event_date > DATE_SUB(cutoff.reporting_cutoff, 28) AND event.event_date <= cutoff.reporting_cutoff
) participation ON participation.student_id = eligible.student_id
  AND participation.academic_term = eligible.academic_term
  AND participation.course_code = eligible.course_code
GROUP BY eligible.faculty, eligible.academic_program, eligible.academic_term, cutoff.reporting_cutoff''',
    "Gold_VR_Financiera.Financial_Collection_Summary": '''CREATE OR REPLACE VIEW "Gold_VR_Financiera"."Financial_Collection_Summary" AS
SELECT
  CASE WHEN EXTRACT(MONTH FROM invoice.invoice_date) BETWEEN 1 AND 7
       THEN CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-01')
       ELSE CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-02') END AS academic_semester,
  cutoff.reporting_cutoff,
  COUNT(*) AS invoices,
  SUM(invoice.total_amount) AS billed_amount,
  SUM(invoice.paid_amount) AS paid_amount,
  SUM(invoice.total_amount - invoice.paid_amount) AS outstanding_amount,
  CAST(100.0 * SUM(invoice.paid_amount) / NULLIF(SUM(invoice.total_amount), 0) AS DECIMAL(5,2)) AS collection_pct
FROM "ERPNext_Postgres".erp.student_invoices invoice
CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
WHERE invoice.invoice_date <= cutoff.reporting_cutoff
GROUP BY CASE WHEN EXTRACT(MONTH FROM invoice.invoice_date) BETWEEN 1 AND 7
       THEN CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-01')
       ELSE CONCAT(CAST(EXTRACT(YEAR FROM invoice.invoice_date) AS VARCHAR), '-02') END,
  cutoff.reporting_cutoff''',
    "Gold_VR_Financiera.Monthly_Collection": '''CREATE OR REPLACE VIEW "Gold_VR_Financiera"."Monthly_Collection" AS
SELECT DATE_TRUNC('month', payment.paid_at) AS collection_month,
  cutoff.reporting_cutoff,
  COUNT(*) AS payments,
  SUM(payment.amount) AS collected_amount
FROM "ERPNext_Postgres".erp.registration_payments payment
CROSS JOIN "Silver"."Demo_Reporting_Cutoff" cutoff
WHERE payment.payment_status IN ('paid', 'partial')
  AND payment.paid_at IS NOT NULL
  AND payment.paid_at <= cutoff.reporting_cutoff
GROUP BY DATE_TRUNC('month', payment.paid_at), cutoff.reporting_cutoff''',
}


def submit_and_wait(session, host, sql):
    """Ejecuta una sentencia Dremio y falla explícitamente si el job no termina."""
    response = session.post(f"{host}/api/v3/sql", json={"sql": sql}, timeout=30)
    response.raise_for_status()
    job_id = response.json()["id"]
    for _ in range(60):
        response = session.get(f"{host}/api/v3/job/{job_id}", timeout=15)
        response.raise_for_status()
        job = response.json()
        if job["jobState"] == "COMPLETED":
            return
        if job["jobState"] in {"FAILED", "CANCELED"}:
            raise RuntimeError(job)
        time.sleep(1)
    raise TimeoutError("Tiempo de espera agotado creando la vista.")


def create_space_if_missing(session, host, name):
    """Crea un space de Dremio; lo considera exitoso si ya existe."""
    response = session.post(f"{host}/api/v3/catalog", json={"entityType": "space", "name": name}, timeout=15)
    if response.status_code in {200, 201, 409}:
        print(f"Space {name} creado o ya existe.")
        return
    existing = session.get(f"{host}/api/v3/catalog/by-name/{urllib.parse.quote(name)}", timeout=15)
    if existing.status_code == 200:
        print(f"Space {name} ya existe.")
        return
    response.raise_for_status()
    existing.raise_for_status()


def main():
    host = os.environ["DREMIO_HOST"]
    session = requests.Session()
    response = session.post(
        f"{host}/apiv2/login",
        json={"userName": os.environ["DREMIO_USERNAME"], "password": os.environ["DREMIO_PASSWORD"]},
        timeout=15,
    )
    response.raise_for_status()
    token = response.json()["token"]
    session.headers["Authorization"] = f"Bearer {token}"
    for name in SPACES:
        create_space_if_missing(session, host, name)
    for name in LEGACY_VIEWS:
        submit_and_wait(session, host, f'DROP VIEW IF EXISTS "University_Lab"."{name}"')
    for name, sql in VIEW_SQL.items():
        submit_and_wait(session, host, sql)
        print(f"{name} creada o actualizada.")


if __name__ == "__main__":
    main()
