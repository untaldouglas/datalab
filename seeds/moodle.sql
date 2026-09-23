-- Datos sintéticos para el origen transaccional Moodle del laboratorio.
-- Este esquema es una representación analítica autónoma; no reemplaza una
-- instalación ni las migraciones oficiales de Moodle.
CREATE SCHEMA IF NOT EXISTS moodle;
SET search_path TO moodle;

CREATE TABLE IF NOT EXISTS users (
  user_id integer PRIMARY KEY,
  username text NOT NULL UNIQUE,
  first_name text NOT NULL,
  last_name text NOT NULL,
  email text NOT NULL UNIQUE,
  role_name text NOT NULL CHECK (role_name IN ('student', 'teacher', 'manager')),
  created_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS courses (
  course_id integer PRIMARY KEY,
  course_code text NOT NULL UNIQUE,
  course_name text NOT NULL,
  category text NOT NULL,
  teacher_id integer NOT NULL REFERENCES users(user_id),
  start_date date NOT NULL,
  end_date date NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'upcoming', 'completed'))
);
CREATE TABLE IF NOT EXISTS enrollments (
  enrollment_id integer PRIMARY KEY,
  user_id integer NOT NULL REFERENCES users(user_id),
  course_id integer NOT NULL REFERENCES courses(course_id),
  enrolled_at timestamptz NOT NULL,
  enrollment_status text NOT NULL CHECK (enrollment_status IN ('active', 'suspended', 'completed')),
  UNIQUE (user_id, course_id)
);
CREATE TABLE IF NOT EXISTS assignments (
  assignment_id integer PRIMARY KEY,
  course_id integer NOT NULL REFERENCES courses(course_id),
  assignment_name text NOT NULL,
  due_at timestamptz NOT NULL,
  max_grade numeric(5,2) NOT NULL
);
CREATE TABLE IF NOT EXISTS assignment_submissions (
  submission_id integer PRIMARY KEY,
  assignment_id integer NOT NULL REFERENCES assignments(assignment_id),
  user_id integer NOT NULL REFERENCES users(user_id),
  submitted_at timestamptz,
  submission_status text NOT NULL CHECK (submission_status IN ('submitted', 'draft', 'missing')),
  grade numeric(5,2),
  feedback text,
  UNIQUE (assignment_id, user_id)
);
CREATE TABLE IF NOT EXISTS quizzes (
  quiz_id integer PRIMARY KEY,
  course_id integer NOT NULL REFERENCES courses(course_id),
  quiz_name text NOT NULL,
  opens_at timestamptz NOT NULL,
  closes_at timestamptz NOT NULL,
  max_grade numeric(5,2) NOT NULL
);
CREATE TABLE IF NOT EXISTS quiz_attempts (
  attempt_id integer PRIMARY KEY,
  quiz_id integer NOT NULL REFERENCES quizzes(quiz_id),
  user_id integer NOT NULL REFERENCES users(user_id),
  attempt_number integer NOT NULL,
  started_at timestamptz NOT NULL,
  finished_at timestamptz,
  attempt_state text NOT NULL CHECK (attempt_state IN ('finished', 'in_progress', 'abandoned')),
  grade numeric(5,2),
  UNIQUE (quiz_id, user_id, attempt_number)
);
CREATE TABLE IF NOT EXISTS forum_posts (
  post_id integer PRIMARY KEY,
  course_id integer NOT NULL REFERENCES courses(course_id),
  user_id integer NOT NULL REFERENCES users(user_id),
  discussion_title text NOT NULL,
  posted_at timestamptz NOT NULL,
  body text NOT NULL
);

TRUNCATE assignment_submissions, quiz_attempts, forum_posts, assignments, quizzes,
  enrollments, courses, users;

INSERT INTO users VALUES
 (1, 'maria.garcia', 'María', 'García', 'maria.garcia@ujmd.edu.sv', 'teacher', '2025-01-10 08:00-06'),
 (2, 'carlos.mejia', 'Carlos', 'Mejía', 'carlos.mejia@ujmd.edu.sv', 'teacher', '2025-01-10 08:00-06'),
 (10, 'ana.lopez', 'Ana', 'López', 'ana.lopez@est.ujmd.edu.sv', 'student', '2026-01-12 09:00-06'),
 (11, 'diego.ruiz', 'Diego', 'Ruiz', 'diego.ruiz@est.ujmd.edu.sv', 'student', '2026-01-12 09:05-06'),
 (12, 'sofia.hernandez', 'Sofía', 'Hernández', 'sofia.hernandez@est.ujmd.edu.sv', 'student', '2026-01-13 10:00-06'),
 (13, 'jose.martinez', 'José', 'Martínez', 'jose.martinez@est.ujmd.edu.sv', 'student', '2026-01-13 10:10-06'),
 (14, 'valeria.castillo', 'Valeria', 'Castillo', 'valeria.castillo@est.ujmd.edu.sv', 'student', '2026-01-14 11:00-06'),
 (15, 'ricardo.santos', 'Ricardo', 'Santos', 'ricardo.santos@est.ujmd.edu.sv', 'student', '2026-01-14 11:10-06');

INSERT INTO courses VALUES
 (101, 'DAT-101', 'Fundamentos de Datos', 'Ingeniería', 1, '2026-01-19', '2026-05-16', 'active'),
 (102, 'ADM-210', 'Gestión Financiera', 'Administración', 2, '2026-01-19', '2026-05-16', 'active'),
 (103, 'DAT-220', 'Analítica Aplicada', 'Ingeniería', 1, '2026-01-19', '2026-05-16', 'active'),
 (104, 'ECO-115', 'Economía Digital', 'Economía', 2, '2026-08-03', '2026-11-28', 'upcoming');

INSERT INTO enrollments VALUES
 (1,10,101,'2026-01-15 08:00-06','active'), (2,11,101,'2026-01-15 08:03-06','active'),
 (3,12,101,'2026-01-15 08:05-06','active'), (4,13,101,'2026-01-15 08:07-06','active'),
 (5,14,102,'2026-01-15 09:00-06','active'), (6,15,102,'2026-01-15 09:02-06','active'),
 (7,10,103,'2026-01-15 09:05-06','active'), (8,12,103,'2026-01-15 09:07-06','active'),
 (9,13,103,'2026-01-15 09:10-06','active'), (10,15,103,'2026-01-15 09:12-06','suspended');

INSERT INTO assignments VALUES
 (1001,101,'Perfilamiento de un conjunto de datos','2026-02-14 23:55-06',100),
 (1002,101,'Modelo relacional universitario','2026-03-14 23:55-06',100),
 (1003,102,'Presupuesto de operación','2026-02-21 23:55-06',100),
 (1004,103,'Tablero de indicadores','2026-03-21 23:55-06',100);
INSERT INTO assignment_submissions VALUES
 (1,1001,10,'2026-02-14 20:15-06','submitted',95,'Buen análisis de valores faltantes.'),
 (2,1001,11,'2026-02-15 00:20-06','submitted',82,'Entrega tardía.'),
 (3,1001,12,'2026-02-14 19:40-06','submitted',91,'Correcto.'),
 (4,1001,13,NULL,'missing',NULL,NULL),
 (5,1002,10,'2026-03-14 18:20-06','submitted',96,'Modelo consistente.'),
 (6,1002,11,'2026-03-14 22:45-06','submitted',78,'Revisar cardinalidades.'),
 (7,1002,12,NULL,'draft',NULL,NULL), (8,1002,13,NULL,'missing',NULL,NULL),
 (9,1003,14,'2026-02-21 17:10-06','submitted',89,'Correcto.'),
 (10,1003,15,'2026-02-22 09:00-06','submitted',74,'Entrega tardía.'),
 (11,1004,10,'2026-03-20 21:05-06','submitted',94,'Excelente visualización.'),
 (12,1004,12,'2026-03-21 23:40-06','submitted',88,'Correcto.'),
 (13,1004,13,NULL,'draft',NULL,NULL), (14,1004,15,NULL,'missing',NULL,NULL);

INSERT INTO quizzes VALUES
 (2001,101,'Diagnóstico SQL','2026-02-01 08:00-06','2026-02-07 23:55-06',20),
 (2002,102,'Flujo de caja','2026-02-08 08:00-06','2026-02-14 23:55-06',20),
 (2003,103,'Indicadores descriptivos','2026-03-01 08:00-06','2026-03-07 23:55-06',20);
INSERT INTO quiz_attempts VALUES
 (1,2001,10,1,'2026-02-03 10:00-06','2026-02-03 10:18-06','finished',18),
 (2,2001,11,1,'2026-02-04 14:00-06','2026-02-04 14:22-06','finished',14),
 (3,2001,12,1,'2026-02-05 09:00-06','2026-02-05 09:25-06','finished',17),
 (4,2001,13,1,'2026-02-07 23:40-06',NULL,'abandoned',NULL),
 (5,2002,14,1,'2026-02-10 11:00-06','2026-02-10 11:14-06','finished',16),
 (6,2002,15,1,'2026-02-13 16:00-06','2026-02-13 16:20-06','finished',13),
 (7,2003,10,1,'2026-03-03 10:00-06','2026-03-03 10:21-06','finished',19),
 (8,2003,12,1,'2026-03-04 13:00-06','2026-03-04 13:24-06','finished',18),
 (9,2003,13,1,'2026-03-07 22:45-06',NULL,'in_progress',NULL);
INSERT INTO forum_posts VALUES
 (1,101,1,'Bienvenida al curso','2026-01-20 08:00-06','Comparte tus expectativas para el curso.'),
 (2,101,10,'Bienvenida al curso','2026-01-20 10:10-06','Me interesa aplicar SQL a datos reales.'),
 (3,101,12,'Dudas sobre normalización','2026-02-12 16:20-06','¿Cómo identificamos una dependencia parcial?'),
 (4,102,14,'Caso de presupuesto','2026-02-18 18:30-06','Comparto mi supuesto de inflación.'),
 (5,103,10,'Visualizaciones','2026-03-10 09:15-06','Propongo comparar retención por cohorte.'),
 (6,103,13,'Visualizaciones','2026-03-11 20:00-06','¿Qué métrica priorizamos para riesgo académico?');

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lab_viewer') THEN
    CREATE ROLE lab_viewer LOGIN PASSWORD 'LabViewerPassword123!';
  END IF;
END
$$;
ALTER ROLE lab_viewer PASSWORD 'LabViewerPassword123!';
GRANT USAGE ON SCHEMA moodle TO lab_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA moodle TO lab_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA moodle GRANT SELECT ON TABLES TO lab_viewer;
