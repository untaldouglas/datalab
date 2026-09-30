# Plan de cierre: demostración institucional

## Propósito

Cerrar la POC demostrando que datos universitarios sintéticos pueden pasar de fuentes transaccionales y objetos a consumo institucional gobernado: dashboards para toma de decisión y respuestas asistidas por IA con trazabilidad.

El alcance de la demo no incluye producción, acceso a datos personales reales, despliegue público, ni propagación automática de clasificación hacia bases, esquemas o tablas. Esa última decisión permanece en espera hasta contar con una política aprobada.

## Resultado demostrable

Una persona de Rectoría, Vicerrectoría o Decanato podrá:

1. Abrir un dashboard con métricas institucionales definidas y actualizadas.
2. Filtrar por periodo, facultad o programa cuando la métrica lo permita.
3. Preguntar en lenguaje natural por una métrica o documento autorizado.
4. Recibir una respuesta con su fuente, definición, fecha de corte y limitaciones.
5. Navegar a OpenMetadata para identificar owner, descripción, clasificación del servicio y lineage de `Student_360`.

## Principios de diseño

- **Métrica antes que visualización:** ninguna gráfica se implementa sin definición, fórmula, owner y granularidad.
- **Dremio es el acceso estructurado:** dashboards y agentes consultan vistas o datasets autorizados de solo lectura; no acceden a las bases transaccionales directamente.
- **MinIO es el origen no estructurado:** los documentos se incorporan mediante un flujo de extracción y recuperación; no se copian sin propósito a un prompt.
- **OpenMetadata aporta contexto, no permiso:** lineage, owner y clasificación orientan el consumo, pero no sustituyen controles de acceso.
- **Respuesta verificable:** toda respuesta de agente debe mostrar fuentes y evitar inventar cifras o políticas.
- **Datos sintéticos:** la demostración se limita a los datos de laboratorio existentes hasta que se apruebe un tratamiento distinto.

## Entregables y orden de trabajo

| Orden | Entregable | Contenido | Criterio de aceptación |
| --- | --- | --- | --- |
| 1 | Contrato de métricas | Catálogo de KPI, fórmula, owner, fuente, periodicidad, filtros y sensibilidad | Borrador [rectoral](metrics/rectoria-kpi-contract.md); cada métrica de demo debe tener una definición aprobada y una consulta Dremio reproducible |
| 2 | Capa de consumo | Vistas Dremio de solo lectura para los KPI y sus agregaciones | Las consultas no exponen filas sensibles innecesarias y sus resultados se reconcilian con las fuentes |
| 3 | Control de acceso de consumo | Identidad no administrativa con `SELECT` sólo sobre resúmenes agregados | La identidad no puede consultar capas internas ni fuentes transaccionales |
| 4 | Dashboards institucionales | Vistas para Rectoría, Vicerrectoría Académica, Vicerrectoría Financiera y Decanatos | Cada audiencia puede responder sus preguntas priorizadas sin SQL manual |
| 5 | Corpus documental | Documentos sintéticos o autorizados en MinIO, con metadatos de origen y alcance | Cada documento recuperable conserva fuente, fecha y clasificación de servicio |
| 6 | Asistente IA | Flujo Langflow y punto de entrada Hermes con herramientas separadas para SQL y documentos | Responde preguntas aprobadas, cita fuentes y rechaza solicitudes fuera de alcance |
| 7 | Guion de demo | Recorrido de principio a fin, datos de preparación, roles y evidencia | Una persona no técnica completa el recorrido sin intervención del equipo técnico |

## Audiencias y preguntas prioritarias

| Audiencia | Preguntas de la demo | Métricas iniciales |
| --- | --- | --- |
| Rectoría | ¿Cómo evoluciona la actividad académica y financiera? ¿Dónde requiere atención la institución? | estudiantes activos, matrícula, actividad Moodle, facturación y saldos agregados |
| Vicerrectoría Académica | ¿Qué programas o cursos muestran menor participación o avance? | matrícula por curso, entregas, intentos de evaluación, actividad por periodo |
| Vicerrectoría Financiera | ¿Cuál es el estado agregado de facturación y cobro estudiantil? | facturas emitidas, saldo pendiente, cobros por periodo |
| Decanatos | ¿Cómo se comportan sus programas, cursos y estudiantes? | matrícula, participación, entregas y alertas agregadas por programa |
| Operación | ¿Están disponibles las fuentes y la calidad mínima del catálogo? | estado de DAGs, `row_count_positive`, freshness y uso de `Student_360` |

Las métricas de riesgo, retención o desempeño institucional no se mostrarán como hechos hasta que su fórmula y fuente de verdad hayan sido aprobadas. La POC puede presentar indicadores operativos y académicos observables, no inferencias automatizadas sobre personas.

Para la demo, el mapeo sintético de organización académica se mantiene en el [contrato de métricas rectorales](metrics/rectoria-kpi-contract.md): Facultad de Ingeniería → Ingeniería → `DAT-101`/`DAT-220`; Facultad de Administración → Administración → `ADM-210`; Facultad de Economía → Economía → `ECO-115`.

## Arquitectura de consumo

```text
Fuentes transaccionales ─┐
MinIO / documentos ─────┼─→ Dremio y vistas autorizadas ─→ Dashboards
                         │
                         └─→ Langflow / Hermes ─→ respuesta con fuentes
                                      │
OpenMetadata ─────────────────────────┘ contexto, owner, lineage y calidad
```

El asistente tendrá dos rutas independientes:

- **Consulta estructurada:** genera o selecciona consultas Dremio de solo lectura sobre vistas aprobadas; devuelve datos agregados y la consulta o vista utilizada.
- **Consulta documental:** recupera fragmentos desde el corpus de MinIO, devuelve citas y declara si no hay evidencia suficiente.

No se habilitarán operaciones de escritura, acceso directo a bases transaccionales, ni recuperación de documentos fuera del corpus aprobado.

## Controles y evidencia

Antes de cada demostración se ejecutará `make check` y `make metadata-verify`. Además, cada dashboard y flujo IA debe registrar:

- fuente Dremio o documento MinIO utilizado;
- owner y fecha de corte de la métrica o documento;
- filtros aplicados;
- resultado esperado para una pregunta de prueba;
- limitaciones conocidas y consultas que debe rechazar.

## Gates de decisión

| Gate | Decisión requerida | Consecuencia si no se aprueba |
| --- | --- | --- |
| KPI | Fórmulas, owners y preguntas prioritarias | No se construyen dashboards con métricas ambiguas |
| BI | Herramienta de dashboard compatible con el stack y la audiencia | Se preparan consultas/vistas, pero no se publica una visualización final |
| Documentos | Corpus sintético o documentos explícitamente autorizados | La ruta documental del agente no se habilita |
| IA | Preguntas permitidas, formato de citas y criterio de rechazo | El asistente permanece en modo demostración técnica, sin usuarios finales |
| Acceso de consumo | Dremio Enterprise/Cloud con RBAC o gateway de consultas permitido | No se conectan dashboards ni agentes; se conservan vistas y pruebas técnicas |
| Clasificación descendiente | Herencia, clasificación por activo o modelo híbrido | Se mantiene como `OUT_OF_SCOPE`; no bloquea dashboards agregados ni el asistente con vistas aprobadas |

## Criterios de cierre

La POC se considera cerrada cuando se demuestran, ante las audiencias definidas:

1. cuatro vistas de dashboard orientadas a sus decisiones;
2. métricas reconciliables con Dremio y documentadas en el contrato;
3. una consulta estructurada y una documental resueltas por el asistente con fuentes visibles;
4. una solicitud fuera de alcance rechazada de forma clara;
5. lineage de `Student_360`, owners y controles de calidad navegables en OpenMetadata;
6. evidencia reproducible de salud y verificación del catálogo.

## Guion de demo (entregable 7)

El recorrido completo para una persona no técnica está en [docs/demo-script.md](demo-script.md): preparación, tableros por audiencia, consultas al asistente con sus pruebas de rechazo, linaje en OpenMetadata y los seis criterios de cierre marcados en vivo. Incluye las preguntas de prueba con sus resultados esperados y las limitaciones que deben declararse ante la audiencia.

## Estado actual

La plataforma base, el catálogo, la calidad mínima, Dremio y la verificación del catálogo están completados. El contrato rectoral y las vistas agregadas están implementados y reconciliados; los tres espacios de oro (`Gold_Rectoria`, `Gold_Decanatos`, `Gold_VR_Financiera`) tienen vistas y tableros Metabase operativos (guion de replicación en [docs/metabase-setup.md](metabase-setup.md)). Las métricas D-01 y F-01 a F-03 del contrato fueron aprobadas por Douglas el 2026-09-30 (F-03 declara `registration_payments.paid_at` como fuente de verdad del cobro). El corpus documental sintético está indexado con búsqueda vectorial y el asistente IA ([entregable 6](../assistant/assistant_api.py)) expone en `http://localhost:8093` sus dos herramientas separadas: consulta estructurada delegada en el gateway y recuperación documental con citas o declaración de evidencia insuficiente. La POC usa Dremio OSS, cuya instancia local no expone grants por vista verificables; por ello se implementó el gateway local descrito en el [ADR 0002](adr/0002-dremio-oss-consumer-access-gate.md). La capa federada adoptó la arquitectura medallion con espacios por audiencia ([ADR 0003](adr/0003-dremio-medallion-audience-spaces.md)). El guion de demo (entregable 7) está publicado en [docs/demo-script.md](demo-script.md). Brecha abierta: los dashboards Metabase y los activos de la capa IA (corpus, índice vectorial, asistente) aún no están catalogados en OpenMetadata; la propuesta de catalogación está en revisión.
