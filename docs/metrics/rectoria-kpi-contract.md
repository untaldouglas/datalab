# Contrato de métricas rectorales — borrador para aprobación

## Estado y propósito

Este documento propone el primer conjunto de indicadores para la demostración institucional. Es un contrato de negocio, no un dashboard ni una consulta ejecutable: cada métrica debe aprobarse antes de materializarse como vista Dremio o visualización.

El alcance usa únicamente datos sintéticos de la POC. No determina desempeño individual, riesgo académico, retención real ni decisiones financieras sobre personas.

## Reglas comunes

- **Fecha de corte:** la fecha y hora de la última consulta o carga incluida en el resultado; debe mostrarse en cada visualización.
- **Periodo académico:** valor `academic_term` del SIS. Ninguna métrica debe asumir que un calendario de la POC equivale al calendario institucional real.
- **Granularidad por defecto:** agregados institucionales, por programa o por curso. No se muestran nombres, correos, IDs ni filas individuales.
- **Fuente de consulta:** las vistas de consumo se crearán en Dremio sobre fuentes de solo lectura. Las fuentes transaccionales no se exponen a dashboards ni agentes.
- **Trazabilidad:** cada métrica mostrará su owner de negocio, fuente Dremio y limitaciones; OpenMetadata permitirá navegar su lineage y calidad.

## Métricas propuestas

| ID | Métrica | Pregunta que responde | Fórmula propuesta | Fuente de verdad | Owner propuesto | Filtros | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Estudiantes registrados | ¿Cuántos estudiantes existen en el SIS para el periodo? | `COUNT(DISTINCT student_id)` de SIS, limitado al periodo si existe matrícula | SIS `students` + `enrollments` | Vicerrectoría Académica | periodo, programa | Requiere aprobación |
| R-02 | Matrículas activas | ¿Cuántas matrículas permanecen activas? | `COUNT(*)` de matrículas con estado `enrolled` | SIS `enrollments` | Vicerrectoría Académica | periodo, curso, programa | Requiere aprobación |
| R-03 | Participación académica observable | ¿Cuántas personas tienen actividad Moodle en el periodo? | personas distintas con entrega, intento de quiz o publicación en foro | Moodle `assignment_submissions`, `quiz_attempts`, `forum_posts` | Vicerrectoría Académica | periodo, curso | Requiere aprobación |
| R-04 | Entregas pendientes | ¿Cuál es el volumen de entregas en estado `draft` o `missing`? | `COUNT(*)` de entregas con esos estados | Moodle `assignment_submissions` | Decanato / Dirección académica | periodo, curso | Requiere aprobación |
| R-05 | Facturación emitida | ¿Cuál es el monto facturado durante el periodo? | `SUM(total_amount)` por `invoice_date` | ERPNext `student_invoices` | Vicerrectoría Financiera | periodo | Requiere aprobación |
| R-06 | Saldo pendiente | ¿Cuál es el saldo agregado aún no pagado? | `SUM(total_amount - paid_amount)` | ERPNext `student_invoices` | Vicerrectoría Financiera | periodo, estado de pago | Requiere aprobación |
| R-07 | Facturas vencidas | ¿Qué monto agregado se encuentra vencido? | `SUM(total_amount - paid_amount)` donde estado es `overdue` | ERPNext `student_invoices` | Vicerrectoría Financiera | periodo | Requiere aprobación |
| R-08 | Cobertura de integración | ¿Qué proporción de registros académicos tiene presencia en la vista federada? | conteo agregado de registros enlazados en `Student_360`; no mide calidad ni éxito académico | Dremio `University_Lab.Student_360` | Dirección de Datos / TI | periodo, programa | Requiere aprobación |

## Decisiones que requieren aprobación

1. **Definición de estudiante registrado:** ¿se cuentan todos los registros SIS, sólo quienes tienen matrícula, o únicamente matrícula activa?
2. **Definición de participación:** ¿una entrega, un intento o una publicación basta para contar actividad? ¿Se excluye la actividad docente?
3. **Unidad financiera:** ¿las métricas se agrupan por fecha de factura, vencimiento, pago o periodo académico?
4. **Organización académica:** el dataset sintético expone `academic_program`; se debe confirmar la equivalencia con facultad, decanato y programa reales antes de usar esos filtros en la demo.
5. **Umbrales y alertas:** la primera demo mostrará valores descriptivos. Ningún valor se etiquetará como alerta, riesgo o incumplimiento sin umbral y owner aprobados.

## Casos que el dashboard y el agente deben rechazar

- “Muéstrame el saldo de una persona específica.”
- “¿Qué estudiante está en riesgo?”
- “Compara el desempeño de docentes individuales.”
- “Calcula la retención institucional” sin una cohorte, periodo y definición aprobados.

Las respuestas deben explicar que la POC opera con agregados sintéticos y que esas solicitudes requieren una política, autorización y modelo de métrica distintos.

## Siguiente entrega tras aprobación

Por cada métrica aprobada se creará una vista Dremio con nombre, SQL, campos de filtro, prueba de reconciliación y referencia a su owner. El tablero rectoral usará esas vistas; Langflow/Hermes sólo podrá consultar el mismo conjunto aprobado.
