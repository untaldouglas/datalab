# Plataforma de Datos Universitaria

Glosario canónico para la iniciativa. Estas definiciones establecen el lenguaje común para documentación, configuración y contribuciones.

## Datos y almacenamiento

**Fuente transaccional**:
Sistema que mantiene los datos operativos originales y es la fuente de referencia de una entidad académica o administrativa.
_Evitar_: base de datos destino, lago de datos

**Fuente SaaS**:
Servicio externo operado por un proveedor que expone datos y metadatos mediante una API, sujeto a sus propios controles de autorización, cuotas y ciclos de cambio.
_Evitar_: base de datos local, integración sin gobierno

**Lakehouse universitario**:
Espacio de datos común que conserva información analítica y objetos compartidos por la plataforma.
_Evitar_: data lake, repositorio de archivos

**Bucket**:
Contenedor lógico dentro del lakehouse para agrupar objetos bajo una política y propósito comunes.
_Evitar_: carpeta, directorio

**Dataset**:
Conjunto identificable de datos con significado, procedencia y responsable definidos.
_Evitar_: tabla suelta, archivo suelto

**Métrica institucional**:
Agregado definido con fórmula, fuente de verdad, owner, fecha de corte y granularidad aprobadas para apoyar una decisión institucional.
_Evitar_: indicador sin fórmula, KPI calculado de manera implícita

**Fecha de corte**:
Instante hasta el cual se consideran los datos de una métrica o respuesta analítica.
_Evitar_: dato al día sin evidencia, tiempo real asumido

**Ventana de participación**:
Periodo móvil de cuatro semanas calendario inmediatamente anteriores a la fecha de corte, usado para medir actividad académica observable.
_Evitar_: actividad histórica sin periodo, último mes ambiguo

**Corte financiero**:
Instante al que se calcula el saldo pendiente o vencido; la emisión se asigna al semestre según la fecha de factura y un cobro, cuando exista su fecha, según la fecha real de pago.
_Evitar_: saldo emitido, cobro estimado

**Cobertura de integración**:
Proporción o conteo agregado de registros que se enlazan entre fuentes aprobadas; no representa calidad, éxito académico ni completitud de negocio por sí sola.
_Evitar_: indicador de desempeño, calidad total

**Estudiante elegible**:
Estudiante con matrícula vigente y pago de matrícula `paid` o `partial`; el estado `partial` habilita temporalmente mientras la matrícula permanezca vigente a la fecha de corte.
_Evitar_: usuario creado, estudiante registrado sin pago de matrícula

**Elegibilidad temporal**:
Habilitación para cursar concedida a un estudiante con pago de matrícula parcial y matrícula vigente a la fecha de corte.
_Evitar_: pago definitivo, matrícula pagada en su totalidad

**Semestre académico**:
Periodo institucional de pregrado: el semestre impar va de enero a julio y el semestre par va de agosto a diciembre.
_Evitar_: mes calendario, periodo sin regla institucional

**Facultad**:
Unidad organizativa responsable de una serie de servicios formativos de pregrado.
_Evitar_: programa formativo, decanato

**Decanato**:
Responsabilidad ejercida por el decano o la decana sobre una facultad.
_Evitar_: facultad, programa formativo

**Programa formativo**:
Oferta académica vigente perteneciente a una facultad.
_Evitar_: facultad, curso aislado

**Servicio formativo**:
Curso u oferta cursable asociado a un programa formativo vigente.
_Evitar_: factura, matrícula, facultad

## Descubrimiento y gobierno

**Federación de datos**:
Consulta unificada de datos que permanecen en sus sistemas de origen o almacenamiento asignado.
_Evitar_: copia centralizada, migración de datos

**Integración personalizada**:
Adaptación mantenida por la plataforma para incorporar metadatos de una fuente que no tiene conector nativo compatible.
_Evitar_: conector oficial, emulación de un protocolo incompatible

**Catálogo de datos**:
Inventario consultable de datasets, servicios y sus metadatos de negocio y técnicos.
_Evitar_: listado de tablas, diccionario aislado

**Metadato**:
Información que describe el significado, estructura, procedencia, calidad o responsable de un activo de datos.
_Evitar_: dato de negocio

**Metadata-as-Code**:
Práctica de expresar el estado deseado de fuentes, gobierno e ingestas de metadatos en manifiestos versionados, validados y revisables antes de aplicarlos.
_Evitar_: configuración manual sin trazabilidad, secretos en archivos de catálogo

**Clasificación universitaria**:
Taxonomía administrada `UniversityClassification` para expresar la sensibilidad de un activo de datos mediante una única etiqueta: `Internal`, `Confidential` o `Restricted`.
_Evitar_: etiquetas de sensibilidad contradictorias, clasificación manual no versionada

**Ingesta de metadatos**:
Proceso programable que extrae metadatos técnicos desde una fuente y los registra en el catálogo de datos sin modificar la fuente.
_Evitar_: carga de datos, sincronización de datos operativos

**Perfilado de datos**:
Proceso que calcula métricas sobre la estructura y contenido de un activo para conocer sus características, sin convertirlo en una copia analítica.
_Evitar_: exportación de datos, muestreo sin control

**Control de calidad de datos**:
Regla ejecutable que evalúa una condición esperada de un activo de datos y registra su resultado para seguimiento.
_Evitar_: validación manual aislada, limpieza de datos

**Owner de datos**:
Persona o equipo responsable de decidir el uso, significado y criterios de calidad de un activo catalogado.
_Evitar_: usuario técnico que solo ejecuta una ingesta, propietario de la infraestructura

**Activo de datos**:
Recurso gobernable que la plataforma identifica, describe y pone a disposición, como un dataset, un bucket o un índice de búsqueda.
_Evitar_: archivo sin contexto, recurso técnico anónimo

## Servicios de la plataforma

**Servicio inicializador**:
Proceso de corta duración que prepara una dependencia antes de que los servicios de larga ejecución puedan iniciar.
_Evitar_: servicio de aplicación, tarea manual

**Servicio de plataforma**:
Proceso de larga ejecución que ofrece una capacidad de datos, búsqueda, IA o gobierno dentro del entorno.
_Evitar_: contenedor auxiliar

**Ejecutor de ingestas**:
Servicio de plataforma que despliega y ejecuta los flujos de ingesta de metadatos. En este entorno se implementa con Apache Airflow y las Managed Airflow APIs de OpenMetadata.
_Evitar_: servidor OpenMetadata, conector manual

**Stack local**:
Conjunto completo de servicios de la iniciativa ejecutado en una sola máquina para desarrollo, demostración o integración.
_Evitar_: entorno de producción
