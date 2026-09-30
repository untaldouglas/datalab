# Metadata-as-Code: plan de implementación

## Objetivo

Convertir el alta y la operación de fuentes de OpenMetadata en un proceso declarativo, repetible, auditable y seguro. El estado deseado se revisa en Git; los secretos y los permisos de ejecución permanecen fuera del repositorio.

## Principios no negociables

- Ningún manifiesto contiene contraseñas, tokens ni claves privadas.
- Una fuente no se publica sin owner, descripción, alcance de lectura y clasificación.
- El perfilado no genera muestras por defecto.
- El agente de IA propone cambios mediante Pull Request; una automatización con identidad separada los aplica tras aprobación.
- Cada tarea tiene criterios de aceptación, evidencia reproducible y validación automatizada.

## Plan de trabajo

| Fase | Tarea | Entregable | Criterio de aceptación | Estado |
| --- | --- | --- | --- | --- |
| 1 | Contrato declarativo | Esquema, validador y manifiesto de Moodle | `make metadata-check` es exitoso; se rechazan secretos y muestreo | Completada |
| 2 | Cobertura de fuentes existentes | Manifiestos para ERP, SIS, ERPNext y Dremio | Un manifiesto validado por fuente y comparación con catálogo | Completada |
| 3 | Planificador | Comando `make metadata-plan` que muestra cambios contra OpenMetadata | Sin mutar servicios; salida revisable en PR | Completada |
| 4 | Aplicador controlado | Comando `make metadata-apply` idempotente para desarrollo | Reejecución sin duplicados; ejecución con identidad dedicada | Completada |
| 5 | Verificación y punto de decisión | `make metadata-verify` con evidencia de inventario, owners, descripciones, DQ, DAGs y lineage; propuesta separada para gobierno de activos | Falla si falta un activo, owner o ejecución esperada; no modifica activos | Completada |
| 6 | Gobierno en CI | Políticas OPA/Conftest y pipeline de Pull Request | Cambios no conformes no pueden fusionarse | Pendiente |
| 7 | Secretos y operación | OpenBao/SOPS, rotación, observabilidad y runbooks | Sin secretos en Git/Compose; alertas y restauración probadas | Pendiente |

## Línea de trabajo adicional: Google Classroom

Google Classroom se gestionará como una fuente SaaS académica, independiente pero dependiente del contrato Metadata-as-Code de la fase 1. No se habilita extracción ni se solicitan credenciales con este plan; cualquier ejecución requiere superar los gates de privacidad, autorización y seguridad definidos en el plan específico.

| Orden | Fase | Dependencia del plan general | Gate de inicio | Estado |
| --- | --- | --- | --- | --- |
| GC-0 | Descubrimiento y gobierno | Fase 1 completada | Owner, privacidad, alcance, campos permitidos y clasificación aprobados | Propuesta |
| GC-1 | Diseño de acceso | Fase 7 | Proyecto institucional y modelo OAuth de mínimo privilegio aprobado | Propuesta |
| GC-2 | Contrato declarativo SaaS | Fase 2 | Extensión versionada para recursos/scopes y referencia de secreto aprobadas | Propuesta |
| GC-3 | Piloto de extracción | Fases 3 y 4 | Credencial de prueba y cursos no productivos disponibles | Propuesta |
| GC-4 | Persistencia y modelado | Fases 4 y 5 | Datasets validados, sin contenido ni calificaciones | Propuesta |
| GC-5 | Catálogo y lineage | Fase 5 | Activos documentados y lineage verificable | Propuesta |
| GC-6 | Operación | Fases 5 y 7 | Alertas, runbook y reejecución idempotente probados | Propuesta |
| GC-7 | Expansión por datos sensibles | Fases 6 y 7 | Aprobación explícita para matrícula, entregas o calificaciones | Propuesta |

El alcance, entregables, evidencia de aceptación, riesgos y condiciones de expansión se detallan en el [plan de Google Classroom](google-classroom-plan.md).

## Entregable de la fase 1

El contrato `CatalogSource` v1alpha1 representa una fuente y su operación mínima:

- identidad de servicio y alcance de bases/esquemas;
- referencia a secreto, nunca el secreto;
- propietario, descripción y clasificación;
- ingestas de metadatos, profiler y calidad;
- programación y zona horaria;
- guardrail de no generar muestras.

El manifiesto [Moodle](../../catalog/sources/moodle-postgres.json) refleja la configuración que ya funciona en la POC. Es declarativo: todavía no crea ni modifica recursos en OpenMetadata. Esa separación permite validar el modelo antes de automatizar cambios productivos.

## Validación y evidencia

Ejecutar:

```bash
make metadata-check
```

Este comando valida la sintaxis de ambos esquemas JSON Schema, valida los manifiestos de referencia y ejecuta catorce pruebas: aceptación de contratos relacional y personalizado, rechazo de una contraseña embebida, rechazo de una API key, rechazo de campos no declarados, rechazo de cron inválido, rechazo de una referencia de secreto multilínea, manejo seguro de tipos JSON inválidos, rechazo de la generación de muestras, validación de operaciones programadas y bajo demanda, rechazo de operaciones personalizadas inventadas, rechazo de capacidades que no existen en Dremio y rechazo de una capacidad personalizada omitida. La salida exitosa es la evidencia mínima de entrega de las fases 1 y 2.

La biblioteca estándar no incorpora un validador completo de JSON Schema Draft 2020-12. Por eso el validador local implementa el contrato cerrado y sus restricciones de seguridad sin dependencias externas; el esquema se verifica sintácticamente y queda disponible para validadores compatibles en CI en la fase 6.

## Decisión técnica inicial

Se usa JSON como formato inicial porque permite una validación reproducible con la biblioteca estándar de Python, sin instalar dependencias nuevas ni introducir credenciales. El esquema JSON Schema deja preparado el contrato para editores y validadores compatibles. En una evolución posterior se puede añadir YAML como representación ergonómica sólo si el pipeline conserva una validación determinista equivalente.

## Entregable de la fase 2

Los manifiestos de [ERP MSSQL](../../catalog/sources/erp-mssql.json), [SIS MSSQL](../../catalog/sources/sis-mssql.json), [ERPNext PostgreSQL](../../catalog/sources/erpnext-postgres.json) y [Dremio Federation](../../catalog/sources/dremio-federation.json) completan la cobertura de las cinco fuentes existentes junto con Moodle.

ERP MSSQL y ERPNext PostgreSQL conservan servicios y motores distintos aunque ambos usen el nombre lógico `erpnext_db`; no se los debe fusionar. SIS y los dos ERP quedan clasificados como `restricted` por contener matrícula, identidad, facturación u operaciones financieras. Esta es una decisión de gobierno declarativa para la POC, no una afirmación de que el tag ya exista en OpenMetadata.

Dremio usa el contrato [CustomCatalogSource](../../catalog/schemas/custom-catalog-source-v1alpha1.schema.json), en vez de simular pipelines relacionales inexistentes. Distingue explícitamente la ausencia de ingesta nativa de metadatos del `metadataBootstrap` idempotente bajo demanda; éste es un script personalizado, mientras lineage y usage son DAGs personalizados. Profiler y Data Quality permanecen en sus fuentes aguas arriba. Las referencias `airflow-secret://` describen el objetivo de operación y no crean secretos ni sustituyen las credenciales de desarrollo existentes.

## Entregable de la fase 3

El comando `make metadata-plan` compara los manifiestos validados con los servicios de bases de datos que expone la API de OpenMetadata. Sólo realiza solicitudes `GET`; no crea, modifica ni despliega servicios, ingestas, owners o etiquetas.

El token JWT se entrega sólo en el entorno de ejecución y nunca se escribe en archivos versionados:

```bash
OPENMETADATA_JWT_TOKEN='token-temporal' make metadata-plan
```

Opcionalmente, se puede apuntar a otra instancia, ajustar el directorio de manifiestos o producir una salida para CI:

```bash
OPENMETADATA_JWT_TOKEN='token-temporal' make metadata-plan \
  METADATA_PLAN_ARGS='--api-url http://localhost:8585/api/v1 --format json'
```

Por cada manifiesto, la salida declara `CREATE` si el servicio no existe, `NO_CHANGE` si coinciden los campos administrados, o `UPDATE` con las diferencias de `serviceType`, descripción, owner y clasificación. La clasificación se contrasta contra las etiquetas de OpenMetadata, aceptando tanto el nombre simple como un FQN terminado en la clasificación (por ejemplo, `PII.Restricted`). El alcance de bases, esquemas, programación e ingestas queda expresamente fuera de esta comparación de servicio; se incorpora al verificador de la fase 5. No se infiere que el gobierno de un servicio ya esté aplicado a sus activos descendientes.

### Validación visual

1. Abre [OpenMetadata](http://localhost:8585) y entra a **Services → Databases**.
2. Busca cada servicio indicado por la salida: `Moodle_Postgres`, `ERP_MSSQL`, `SIS_MSSQL`, `ERPNext_Postgres` y `Dremio_Federation`.
3. Para una fila `NO_CHANGE`, compara en la ficha del servicio su tipo, descripción, owner y etiquetas con el manifiesto correspondiente.
4. Para `CREATE`, confirma que el servicio no figura en la lista. Para `UPDATE`, abre la ficha y contrasta cada campo listado bajo la fila.
5. Recarga la página al terminar: debe permanecer idéntica. Esa ausencia de mutaciones es el criterio principal de aceptación de la fase 3.

## Entregable de la fase 4

`make metadata-apply` aplica únicamente los cambios de gobierno declarados y exige una confirmación explícita. Antes de usarlo, revisa la salida de `make metadata-plan`.

```bash
OPENMETADATA_JWT_TOKEN='token-temporal' make metadata-apply \
  METADATA_APPLY_ARGS='--confirm'
```

El aplicador conserva los tags que no pertenecen a la taxonomía administrada y sincroniza descripciones, owners y clasificación **solamente en los Database Services**. Si falta, crea la clasificación `UniversityClassification` y sus tres etiquetas mutuamente excluyentes: `Internal`, `Confidential` y `Restricted`. El manifiesto `internal`, `confidential` o `restricted` se asocia respectivamente con una de esas etiquetas. Reejecutar el comando no duplica tags ni vuelve a parchear un servicio que ya coincide.

Una fuente ausente, o una cuyo tipo de servicio no coincida, queda en estado `BLOCKED`: el aplicador no puede ni debe inventar o reemplazar la configuración de conexión ni el secreto que un servicio de OpenMetadata requiere. Esa creación o migración queda condicionada al gestor de secretos y la identidad dedicada de la fase 7.

Después de aplicar, ejecuta otra vez `make metadata-plan`. El resultado esperado es `NO_CHANGE` para las fuentes existentes. En OpenMetadata, abre el detalle de cada **Database Service** y valida la descripción, owner y etiqueta `UniversityClassification.*`. La interfaz normalmente muestra sólo el nombre corto de la etiqueta, por ejemplo `Internal` en lugar de `UniversityClassification.Internal`.

## Límite actual: servicios frente a Data Assets

OpenMetadata muestra una jerarquía de entidades, no un único objeto por fuente:

```text
Database Service                 ← fases 3 y 4: planificado y sincronizado
└── Database                     ← actualmente ingerido; owner y descripción existentes
    └── Database Schema          ← actualmente ingerido; owner y descripción existentes
        └── Table / View         ← actualmente ingerido; owner y descripción existentes
```

Las etiquetas asignadas al servicio no se copian automáticamente a `Database`, `Database Schema` ni `Table/View`. Por tanto, que Explore muestre `No Tags added` en `moodle_db` no contradice un `NO_CHANGE` del planificador: ambos resultados corresponden a niveles distintos.

El inventario esperado en Explore es de cinco bases, cinco esquemas y diecinueve tablas o vistas: las cuatro fuentes transaccionales aportan cuatro bases, cuatro esquemas y dieciocho tablas; Dremio añade `Dremio.University_Lab.Student_360` como una base, un esquema y una vista federada. Los owners y las descripciones de esos activos ya existen por las ingestas; las clasificaciones de activos descendientes aún no están declaradas ni sincronizadas.

## Entregable de la fase 5: verificación y punto de decisión

`make metadata-verify` es una comprobación de solo lectura. Requiere credenciales de OpenMetadata y Airflow únicamente en el entorno de ejecución; no persiste secretos:

```bash
OPENMETADATA_JWT_TOKEN='token-temporal' \
AIRFLOW_USERNAME='usuario-temporal' \
AIRFLOW_PASSWORD='contraseña-temporal' \
make metadata-verify
```

Produce evidencia por nivel de entidad y falla si se incumple alguno de estos mínimos:

- existen las cinco fuentes, sus cinco bases y cinco esquemas esperados;
- existen las dieciocho tablas transaccionales y la vista `Student_360`;
- cada activo esperado tiene owner y descripción;
- los cuatro pipelines de metadata, profiler y Data Quality tienen una ejecución esperada;
- `Student_360` conserva sus cuatro dependencias de lineage aprobadas.

La salida distingue `PASS`, `FAIL` y `OUT_OF_SCOPE`. `OUT_OF_SCOPE` cubre expresamente las etiquetas de bases, esquemas y tablas, para que una ausencia de clasificación no se confunda con una falla de ingesta.

Con esa evidencia se hará un punto de análisis antes de mutar Data Assets. La decisión requerida será si la clasificación de un servicio debe propagarse a todos sus descendientes, si debe declararse por activo, o si algunos activos deben tener una clasificación más restrictiva. Hasta que esa política sea aprobada y declarada, ninguna automatización aplicará etiquetas a Database, Database Schema o Table/View.
