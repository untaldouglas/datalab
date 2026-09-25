# Plan de trabajo: Google Classroom

## Propósito y relación con el plan principal

Incorporar Google Classroom como **fuente SaaS académica** mediante una integración por API, segura y repetible. Este plan es una línea de trabajo adicional al plan principal de [Metadata-as-Code](README.md): reutiliza su contrato declarativo, validaciones, despliegue controlado y verificaciones. No lo sustituye ni adelanta sus dependencias.

La integración no comienza con datos personales, calificaciones, adjuntos ni contenido de estudiantes. El primer producto es un catálogo técnico y una extracción piloto de cursos y tareas autorizadas.

## Principios de operación

- Extraer sólo por API oficial y en modo lectura.
- Aplicar mínimo privilegio y scopes incrementales.
- Separar identidad, matrícula, actividad, entregas y archivos adjuntos en activos con clasificación independiente.
- No almacenar secretos en Git, manifiestos, DAGs ni Compose.
- No generar muestras de datos en OpenMetadata.
- Mantener trazabilidad desde API hasta MinIO, Dremio y OpenMetadata.
- Requerir aprobación humana antes de ampliar a datos de estudiantes o calificaciones.

## Plan propuesto

| Fase | Objetivo | Entregables | Criterio de aceptación y evidencia | Estado |
| --- | --- | --- | --- | --- |
| GC-0 | Descubrimiento y gobierno | Registro de owner académico/técnico, propósito, cursos piloto, clasificación, retención, decisión de privacidad y allowlist de campos | Acta aprobada por académica, privacidad y seguridad; inventario campo a campo permitido/prohibido; no se crea credencial | Propuesta |
| GC-1 | Diseño de acceso | Decisión OAuth, listado de scopes, identidad de ejecución y referencia de secreto | Revisión de seguridad aprueba mínimo privilegio; secreto sólo referido como `openbao://` o `airflow-secret://` | Propuesta |
| GC-2 | Contrato declarativo SaaS | Extensión versionada del contrato —nuevo kind o versión— para recursos API, scopes permitidos, aprobación asociada y exclusiones de campos | Pruebas aceptan sólo recursos/scopes en allowlist y rechazan secretos, muestreo, campos o scopes no aprobados; no se reutiliza forzosamente el contrato relacional | Propuesta |
| GC-3 | Piloto de extracción | Adaptador Airflow de sólo lectura, paginación, checkpoint, reintentos, auditoría y proyección de allowlist | Ejecución exitosa sobre cursos de prueba; conteos reconciliados; evidencia automatizada de que estudiantes, calificaciones, adjuntos, texto libre y campos excluidos no alcanzan raw, logs ni catálogo | Propuesta |
| GC-4 | Persistencia y modelado | Zona raw particionada en MinIO y datasets normalizados de cursos/tareas, construidos sólo desde la proyección aprobada | Particiones reproducibles; hashes y frescura verificados; DQ de identificadores, fechas y duplicados; prueba de ausencia de campos excluidos | Propuesta |
| GC-5 | Catálogo y lineage | Servicio/datasets en OpenMetadata, owners, descripciones, clasificación, DQ y lineage | Activos visibles en Explore; owner y descripción completos; lineage API → raw → Dremio verificado | Propuesta |
| GC-6 | Operación | Alertas, runbook, métricas de latencia/error y proceso de recuperación | Simulación de fallo y reejecución idempotente con evidencia | Propuesta |
| GC-7 | Expansión por datos sensibles | Solicitud de cambio para matrícula, entregas o calificaciones | Aprobación académica, legal y de privacidad; scopes y pruebas adicionales aprobadas antes de desplegar | Propuesta |

## Alcance por oleadas

| Oleada | Incluye | Excluye expresamente | Decisión requerida |
| --- | --- | --- | --- |
| A: catálogo piloto | Cursos, estado y fechas; tareas y fechas de vencimiento incluidos en la allowlist aprobada | Matrícula, entregas, calificaciones, adjuntos y texto libre | Owner académico, privacidad y seguridad |
| B: participación | Matrícula pseudonimizada y métricas agregadas de actividad | Calificaciones, respuestas y adjuntos | Privacidad y gobierno de datos |
| C: rendimiento | Estado de entrega y calificaciones con propósito definido | Contenido de archivos o respuestas salvo aprobación separada | Académica, legal, privacidad y seguridad |

## Decisión de autenticación

Se evaluarán dos opciones, sin configurar ninguna hasta GC-1:

| Opción | Uso | Ventajas | Limitaciones | Decisión provisional |
| --- | --- | --- | --- | --- |
| OAuth 3LO con cuenta institucional dedicada | Piloto limitado | Alcance acotado y revocable; menor privilegio inicial | Cobertura limitada a cursos disponibles para esa cuenta | Recomendada para GC-3 |
| Cuenta de servicio con delegación de dominio | Operación institucional | Automatizable y escalable | Mayor radio de impacto; exige controles administrativos y auditoría reforzada | Reservada para GC-7 o cuando la cobertura lo justifique |

Los scopes se incorporan de manera acumulativa y revisable. Para la oleada A, GC-1 puede aprobar lectura de cursos y el scope de coursework estrictamente necesario para obtener las tareas y fechas incluidas en la allowlist; el adaptador proyecta sólo esos campos y no persiste notas, entregas ni texto libre. Matrícula se incorpora después. Entregas y calificaciones requieren una aprobación independiente. No se añade acceso a Drive en este plan: adjuntos y archivos requieren una evaluación separada.

## Arquitectura objetivo

```text
Google Classroom API
  → Airflow extractor (read-only, incremental)
  → MinIO raw (particionado, con hash)
  → normalización y controles DQ
  → Dremio views gobernadas
  → OpenMetadata (catálogo, calidad y lineage)
```

El adaptador debe usar checkpoints por recurso y fecha, paginación, reintentos con backoff, límites de concurrencia, una zona raw inmutable y reejecución idempotente. Las credenciales las consume únicamente el ejecutor; OpenMetadata recibe metadatos, no tokens ni datos de muestra.

## Datos mínimos de cada entregable

Cada fase debe registrar en el Pull Request o evidencia equivalente:

1. Propósito, owner, ambiente y clasificación.
2. Alcance de recursos y allowlist de campos incluidos/excluidos.
3. Scopes solicitados y justificación.
4. Referencia de secreto, sin material secreto.
5. Comandos de validación y resultado.
6. Conteos, frescura, controles DQ y lineage esperado.
7. Riesgo residual, procedimiento de reversión y responsable operativo.

## Criterios de detención

La línea se detiene y no avanza si falta cualquiera de estas condiciones:

- Owner académico o propósito de uso aprobados.
- Decisión de privacidad o allowlist de campos ausente.
- Scope que excede la oleada acordada.
- Credencial fuera del gestor de secretos o con permisos de escritura.
- Datos restringidos en logs, manifestos, muestras o catálogo sin aprobación.
- Fallo de reconciliación, DQ, lineage o reejecución idempotente.

## Próxima tarea gestionable

La primera tarea cuando se autorice esta línea es **GC-0: descubrimiento y gobierno**. No necesita conexión a Google Classroom: produce la matriz de alcance y clasificación, identifica owners y deja explícitas las decisiones que deben aprobarse antes de solicitar OAuth.
