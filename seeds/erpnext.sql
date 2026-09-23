-- Datos sintéticos para la fuente ERP del laboratorio.
-- No son una exportación ni una sustitución del esquema oficial de ERPNext.
IF DB_ID(N'erpnext_db') IS NULL CREATE DATABASE erpnext_db;
GO
USE erpnext_db;
GO
IF SCHEMA_ID(N'erp') IS NULL EXEC(N'CREATE SCHEMA erp');
GO
DROP TABLE IF EXISTS erp.sales_invoice_item;
DROP TABLE IF EXISTS erp.sales_invoice;
DROP TABLE IF EXISTS erp.purchase_order_item;
DROP TABLE IF EXISTS erp.purchase_order;
DROP TABLE IF EXISTS erp.item;
DROP TABLE IF EXISTS erp.customer;
DROP TABLE IF EXISTS erp.supplier;
GO
CREATE TABLE erp.customer (
  customer_id int PRIMARY KEY, customer_name nvarchar(120) NOT NULL,
  customer_group nvarchar(60) NOT NULL, territory nvarchar(60) NOT NULL,
  created_at datetime2 NOT NULL
);
CREATE TABLE erp.supplier (
  supplier_id int PRIMARY KEY, supplier_name nvarchar(120) NOT NULL,
  supplier_group nvarchar(60) NOT NULL, country nvarchar(60) NOT NULL
);
CREATE TABLE erp.item (
  item_id int PRIMARY KEY, item_code nvarchar(40) NOT NULL UNIQUE,
  item_name nvarchar(160) NOT NULL, item_group nvarchar(60) NOT NULL,
  standard_rate decimal(12,2) NOT NULL, is_stock_item bit NOT NULL
);
CREATE TABLE erp.sales_invoice (
  invoice_id int PRIMARY KEY, invoice_number nvarchar(30) NOT NULL UNIQUE,
  customer_id int NOT NULL REFERENCES erp.customer(customer_id),
  posting_date date NOT NULL, due_date date NOT NULL,
  status nvarchar(20) NOT NULL CHECK (status IN ('Paid','Unpaid','Overdue','Draft')),
  grand_total decimal(12,2) NOT NULL
);
CREATE TABLE erp.sales_invoice_item (
  invoice_item_id int PRIMARY KEY, invoice_id int NOT NULL REFERENCES erp.sales_invoice(invoice_id),
  item_id int NOT NULL REFERENCES erp.item(item_id), qty decimal(10,2) NOT NULL,
  rate decimal(12,2) NOT NULL, amount decimal(12,2) NOT NULL
);
CREATE TABLE erp.purchase_order (
  purchase_order_id int PRIMARY KEY, po_number nvarchar(30) NOT NULL UNIQUE,
  supplier_id int NOT NULL REFERENCES erp.supplier(supplier_id),
  transaction_date date NOT NULL, schedule_date date NOT NULL,
  status nvarchar(20) NOT NULL CHECK (status IN ('To Receive','Completed','Cancelled')),
  grand_total decimal(12,2) NOT NULL
);
CREATE TABLE erp.purchase_order_item (
  purchase_order_item_id int PRIMARY KEY, purchase_order_id int NOT NULL REFERENCES erp.purchase_order(purchase_order_id),
  item_id int NOT NULL REFERENCES erp.item(item_id), qty decimal(10,2) NOT NULL,
  rate decimal(12,2) NOT NULL, amount decimal(12,2) NOT NULL
);
GO
INSERT INTO erp.customer VALUES
 (1,N'Universidad Dr. José Matías Delgado',N'Institución educativa',N'San Salvador','2025-11-01'),
 (2,N'Centro de Formación Continua',N'Institución educativa',N'San Salvador','2025-11-08'),
 (3,N'Fundación Innovar',N'Organización sin fines de lucro',N'La Libertad','2025-12-02');
INSERT INTO erp.supplier VALUES
 (1,N'Tecnología Educativa Centroamericana',N'Tecnología',N'El Salvador'),
 (2,N'Papelería Académica',N'Oficina',N'El Salvador'),
 (3,N'Cloud Servicios Regionales',N'Tecnología',N'Costa Rica');
INSERT INTO erp.item VALUES
 (1,N'LIC-LMS-ANUAL',N'Licencia anual de plataforma LMS',N'Servicios digitales',2400,0),
 (2,N'CAP-DATOS',N'Curso de analítica de datos',N'Formación',180,0),
 (3,N'KIT-LAB-DATOS',N'Kit de laboratorio de datos',N'Equipamiento',95,1),
 (4,N'SOP-LAPTOP',N'Soporte para laptop',N'Oficina',32.50,1),
 (5,N'SRV-CLOUD-MES',N'Infraestructura cloud mensual',N'Servicios digitales',850,0);
INSERT INTO erp.sales_invoice VALUES
 (1,N'SINV-2026-0001',1,'2026-01-15','2026-02-14',N'Paid',2400),
 (2,N'SINV-2026-0002',2,'2026-02-03','2026-03-05',N'Paid',1080),
 (3,N'SINV-2026-0003',3,'2026-03-10','2026-04-09',N'Overdue',570),
 (4,N'SINV-2026-0004',1,'2026-03-20','2026-04-19',N'Unpaid',360);
INSERT INTO erp.sales_invoice_item VALUES
 (1,1,1,1,2400,2400), (2,2,2,6,180,1080), (3,3,3,6,95,570), (4,4,2,2,180,360);
INSERT INTO erp.purchase_order VALUES
 (1,N'PO-2026-0001',1,'2026-01-05','2026-01-20',N'Completed',1900),
 (2,N'PO-2026-0002',2,'2026-02-12','2026-02-28',N'Completed',650),
 (3,N'PO-2026-0003',3,'2026-03-15','2026-04-01',N'To Receive',1700);
INSERT INTO erp.purchase_order_item VALUES
 (1,1,3,20,95,1900), (2,2,4,20,32.50,650), (3,3,5,2,850,1700);
GO
