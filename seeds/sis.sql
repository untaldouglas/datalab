-- Fuente SIS sintética; la clave student_id enlaza SIS, Moodle y ERPNext.
IF DB_ID(N'sis_db') IS NULL CREATE DATABASE sis_db;
GO
USE sis_db;
GO
IF SCHEMA_ID(N'sis') IS NULL EXEC(N'CREATE SCHEMA sis');
GO
DROP TABLE IF EXISTS sis.enrollments;
DROP TABLE IF EXISTS sis.students;
GO
CREATE TABLE sis.students (
  student_id nvarchar(20) PRIMARY KEY,
  university_email nvarchar(160) NOT NULL UNIQUE,
  full_name nvarchar(160) NOT NULL,
  academic_program nvarchar(120) NOT NULL,
  student_status nvarchar(20) NOT NULL CHECK (student_status IN ('active', 'suspended'))
);
CREATE TABLE sis.enrollments (
  enrollment_id integer PRIMARY KEY,
  student_id nvarchar(20) NOT NULL REFERENCES sis.students(student_id),
  academic_term nvarchar(20) NOT NULL,
  course_code nvarchar(30) NOT NULL,
  enrollment_status nvarchar(20) NOT NULL CHECK (enrollment_status IN ('enrolled', 'withdrawn'))
);
INSERT INTO sis.students VALUES
 (N'STU-1001', N'ana.lopez@est.ujmd.edu.sv', N'Ana López', N'Ingeniería de Datos', N'active'),
 (N'STU-1002', N'diego.ruiz@est.ujmd.edu.sv', N'Diego Ruiz', N'Ingeniería de Datos', N'active'),
 (N'STU-1003', N'sofia.hernandez@est.ujmd.edu.sv', N'Sofía Hernández', N'Ingeniería de Datos', N'active'),
 (N'STU-1004', N'jose.martinez@est.ujmd.edu.sv', N'José Martínez', N'Ingeniería de Datos', N'active'),
 (N'STU-1005', N'valeria.castillo@est.ujmd.edu.sv', N'Valeria Castillo', N'Administración', N'active'),
 (N'STU-1006', N'ricardo.santos@est.ujmd.edu.sv', N'Ricardo Santos', N'Ingeniería de Datos', N'suspended');
INSERT INTO sis.enrollments VALUES
 (1, N'STU-1001', N'2026-01', N'DAT-101', N'enrolled'),
 (2, N'STU-1002', N'2026-01', N'DAT-101', N'enrolled'),
 (3, N'STU-1003', N'2026-01', N'DAT-101', N'enrolled'),
 (4, N'STU-1004', N'2026-01', N'DAT-101', N'enrolled'),
 (5, N'STU-1005', N'2026-01', N'ADM-210', N'enrolled'),
 (6, N'STU-1006', N'2026-01', N'DAT-220', N'withdrawn');
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'lab_viewer')
  CREATE USER [lab_viewer] FOR LOGIN [lab_viewer];
GRANT SELECT ON SCHEMA::sis TO [lab_viewer];
GO
