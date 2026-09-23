-- Fuente transaccional ERPNext sintética para consolidación académica.
CREATE SCHEMA IF NOT EXISTS erp;
SET search_path TO erp;

CREATE TABLE IF NOT EXISTS student_invoices (
  invoice_id integer PRIMARY KEY,
  invoice_number text NOT NULL UNIQUE,
  student_id text NOT NULL,
  invoice_date date NOT NULL,
  due_date date NOT NULL,
  total_amount numeric(12,2) NOT NULL,
  paid_amount numeric(12,2) NOT NULL,
  payment_status text NOT NULL CHECK (payment_status IN ('paid', 'partial', 'unpaid', 'overdue'))
);

TRUNCATE student_invoices;
INSERT INTO student_invoices VALUES
 (1, 'SINV-PG-0001', 'STU-1001', '2026-01-15', '2026-02-14', 420.00, 420.00, 'paid'),
 (2, 'SINV-PG-0002', 'STU-1002', '2026-01-15', '2026-02-14', 420.00, 300.00, 'partial'),
 (3, 'SINV-PG-0003', 'STU-1003', '2026-02-15', '2026-03-14', 420.00, 0.00, 'overdue'),
 (4, 'SINV-PG-0004', 'STU-1004', '2026-02-15', '2026-03-14', 420.00, 420.00, 'paid'),
 (5, 'SINV-PG-0005', 'STU-1005', '2026-03-15', '2026-04-14', 420.00, 0.00, 'unpaid'),
 (6, 'SINV-PG-0006', 'STU-1006', '2026-03-15', '2026-04-14', 420.00, 420.00, 'paid');

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lab_viewer') THEN
    CREATE ROLE lab_viewer LOGIN PASSWORD 'LabViewerPassword123!';
  END IF;
END
$$;
ALTER ROLE lab_viewer PASSWORD 'LabViewerPassword123!';
GRANT USAGE ON SCHEMA erp TO lab_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA erp TO lab_viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA erp GRANT SELECT ON TABLES TO lab_viewer;
