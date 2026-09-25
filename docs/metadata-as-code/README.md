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
| 2 | Cobertura de fuentes existentes | Manifiestos para ERP, SIS, ERPNext y Dremio | Un manifiesto validado por fuente y comparación con catálogo | Pendiente |
| 3 | Planificador | Comando `plan` que muestra cambios contra OpenMetadata | Sin mutar servicios; salida revisable en PR | Pendiente |
| 4 | Aplicador controlado | Comando `apply` idempotente para desarrollo | Reejecución sin duplicados; ejecución con identidad dedicada | Pendiente |
| 5 | Verificación | Comando `verify` y evidencia de conteos, owners, DQ y DAGs | Falla si falta un activo, owner o ejecución esperada | Pendiente |
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

Este comando valida la sintaxis del esquema JSON Schema, valida el manifiesto de referencia y ejecuta ocho pruebas: aceptación del manifiesto real, rechazo de una contraseña embebida, rechazo de una API key, rechazo de campos no declarados, rechazo de cron inválido, rechazo de una referencia de secreto multilínea, manejo seguro de tipos JSON inválidos y rechazo de la generación de muestras. La salida exitosa es la evidencia mínima de entrega de esta fase.

La biblioteca estándar no incorpora un validador completo de JSON Schema Draft 2020-12. Por eso el validador local implementa el contrato cerrado y sus restricciones de seguridad sin dependencias externas; el esquema se verifica sintácticamente y queda disponible para validadores compatibles en CI en la fase 6.

## Decisión técnica inicial

Se usa JSON como formato inicial porque permite una validación reproducible con la biblioteca estándar de Python, sin instalar dependencias nuevas ni introducir credenciales. El esquema JSON Schema deja preparado el contrato para editores y validadores compatibles. En la fase 2 se puede añadir YAML como representación ergonómica sólo si el pipeline conserva una validación determinista equivalente.
