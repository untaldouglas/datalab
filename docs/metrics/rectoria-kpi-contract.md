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
| R-01 | Estudiantes elegibles | ¿Cuántos estudiantes han pagado matrícula para cursar un servicio formativo vigente? | `COUNT(DISTINCT student_id)` con matrícula pagada y servicio vigente | Matrícula/pago + SIS `enrollments` | Vicerrectoría Académica | semestre, facultad, programa | Requiere regla de enlace |
| R-02 | Matrículas activas | ¿Cuántas matrículas permanecen activas? | `COUNT(*)` de matrículas con estado `enrolled` | SIS `enrollments` | Vicerrectoría Académica | periodo, curso, programa | Requiere aprobación |
| R-03 | Participación académica observable | ¿Cuántos estudiantes elegibles tienen evidencia reciente de actividad Moodle? | estudiantes distintos con al menos una entrega `submitted`, intento de quiz `finished` o publicación propia en foro durante las cuatro semanas anteriores a la fecha de corte; excluye docentes y estados `draft`/`missing` | Moodle `assignment_submissions`, `quiz_attempts`, `forum_posts` + matrícula elegible | Vicerrectoría Académica | semestre, facultad, programa, curso | Aprobada |
| R-04 | Entregas pendientes | ¿Cuál es el volumen de entregas en estado `draft` o `missing`? | `COUNT(*)` de entregas con esos estados | Moodle `assignment_submissions` | Decanato / Dirección académica | periodo, curso | Requiere aprobación |
| R-05 | Facturación emitida | ¿Cuál es el monto facturado durante el semestre? | `SUM(total_amount)` por `invoice_date`; la emisión se asigna al semestre de esa fecha | ERPNext `student_invoices` | Vicerrectoría Financiera | semestre | Aprobada |
| R-06 | Saldo pendiente | ¿Cuál es el saldo agregado aún no pagado a la fecha de corte? | `SUM(total_amount - paid_amount)` al corte, aun si la factura se emitió antes | ERPNext `student_invoices` | Vicerrectoría Financiera | fecha de corte, estado de pago | Aprobada |
| R-07 | Facturas vencidas | ¿Qué monto agregado se encuentra vencido a la fecha de corte? | `SUM(total_amount - paid_amount)` donde estado es `overdue`, al corte | ERPNext `student_invoices` | Vicerrectoría Financiera | fecha de corte | Aprobada |
| R-08 | Cobertura de integración | ¿Qué proporción de registros académicos tiene presencia en la vista federada? | conteo agregado de registros enlazados en `Student_360`; no mide calidad ni éxito académico | Dremio `University_Lab.Student_360` | Dirección de Datos / TI | periodo, programa | Requiere aprobación |

## Decisiones que requieren aprobación

1. **Regla de estudiante elegible:** aprobada como pago de matrícula más servicio formativo vigente. La POC requiere aún vincular explícitamente el pago, el servicio y el semestre: `student_invoices` contiene estado y monto de factura, pero no representa por sí solo el pago de matrícula de un servicio vigente.
2. **Definición de participación:** aprobada como al menos una entrega enviada, un quiz finalizado o una publicación propia de estudiante durante las cuatro semanas anteriores a la fecha de corte. No cuentan `draft`, `missing` ni actividad docente.
3. **Semestre académico y corte financiero:** aprobado para pregrado: impar de enero a julio y par de agosto a diciembre. La facturación se asigna por `invoice_date`; saldos y vencimientos se calculan a la fecha de corte. Cuando exista una tabla de pagos, los cobros se asignarán por su fecha real de pago. La capa Dremio deberá mapear fechas y el valor actual `academic_term` a esta regla.
4. **Organización académica:** aprobada la jerarquía Facultad → Programa Formativo, con Decanato como responsabilidad de la Facultad. El dataset sintético expone `academic_program`; se debe añadir o mapear la Facultad antes de usar el filtro de Decanato.
5. **Umbrales y alertas:** se proponen abajo para aprobación. La primera demo no etiquetará personas como “en riesgo”.

## Ejemplo de participación académica

Con fecha de corte el 31 de marzo, Ana tiene una matrícula elegible en `DAT-101` y envía una tarea el 20 de marzo: cuenta como participante. Diego está matriculado pero sólo tiene una tarea en estado `draft`: no cuenta. La publicación de María, docente del curso, tampoco cuenta porque la métrica se limita a estudiantes. Un evento de Ana del 20 de febrero quedaría fuera de la ventana de cuatro semanas.

El resultado que ve Rectoría es agregado, por ejemplo: “78 % de estudiantes elegibles tuvo al menos una actividad observable”; no muestra nombres ni lista de estudiantes sin actividad.

## Alertas propuestas para la demo

| Alerta | Regla agregada propuesta | Audiencia | Límite |
| --- | --- | --- | --- |
| Participación baja por curso | Proporción de estudiantes elegibles sin evento observable en las cuatro semanas previas a la fecha de corte, mayor a un umbral aprobado | Vicerrectoría Académica / Decanato | Describe actividad observable; no diagnostica riesgo individual |
| Entregas pendientes elevadas | Proporción de entregas `draft` o `missing` mayor a un umbral aprobado | Decanato / Dirección académica | Se revisa por curso o programa, sin listar estudiantes |
| Saldo vencido agregado | Monto pendiente de facturas `overdue` superior al umbral financiero aprobado | Vicerrectoría Financiera | No expone saldos individuales |
| Salud de operación | Un DAG crítico no termina en `success` o falla `row_count_positive` | Dirección de Datos / TI | Es alerta técnica, no académica ni financiera |

Los umbrales iniciales deben aprobarlos los owners. Para la demo se pueden presentar como estados descriptivos —por ejemplo, “requiere revisión”— y no como sanciones, riesgo o conclusiones sobre personas.

## Casos que el dashboard y el agente deben rechazar

- “Muéstrame el saldo de una persona específica.”
- “¿Qué estudiante está en riesgo?”
- “Compara el desempeño de docentes individuales.”
- “Calcula la retención institucional” sin una cohorte, periodo y definición aprobados.

Las respuestas deben explicar que la POC opera con agregados sintéticos y que esas solicitudes requieren una política, autorización y modelo de métrica distintos.

## Siguiente entrega tras aprobación

Por cada métrica aprobada se creará una vista Dremio con nombre, SQL, campos de filtro, prueba de reconciliación y referencia a su owner. El tablero rectoral usará esas vistas; Langflow/Hermes sólo podrá consultar el mismo conjunto aprobado.
