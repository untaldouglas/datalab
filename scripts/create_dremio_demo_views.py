#!/usr/bin/env python3
"""Crea de forma idempotente las vistas Dremio aprobadas para la demo."""
import os
import time
import requests

SQL = '''CREATE OR REPLACE VIEW "University_Lab"."Eligible_Student_Activity" AS
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
WHERE r.registration_status = 'vigente' AND e.enrollment_status = 'enrolled' AND p.payment_status IN ('paid', 'partial')'''

session = requests.Session()
token = session.post(f"{os.environ['DREMIO_HOST']}/apiv2/login", json={"userName": os.environ['DREMIO_USERNAME'], "password": os.environ['DREMIO_PASSWORD']}, timeout=15).json()['token']
session.headers['Authorization'] = f'Bearer {token}'
job_id = session.post(f"{os.environ['DREMIO_HOST']}/api/v3/sql", json={"sql": SQL}, timeout=30).json()['id']
for _ in range(60):
    job = session.get(f"{os.environ['DREMIO_HOST']}/api/v3/job/{job_id}", timeout=15).json()
    if job['jobState'] == 'COMPLETED':
        print('Eligible_Student_Activity creada o actualizada.')
        break
    if job['jobState'] in {'FAILED', 'CANCELED'}:
        raise SystemExit(job)
    time.sleep(1)
else:
    raise SystemExit('Tiempo de espera agotado creando la vista.')
