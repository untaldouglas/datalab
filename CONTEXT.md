# Plataforma de Datos Universitaria

Glosario canónico para la iniciativa. Estas definiciones establecen el lenguaje común para documentación, configuración y contribuciones.

## Datos y almacenamiento

**Fuente transaccional**:
Sistema que mantiene los datos operativos originales y es la fuente de referencia de una entidad académica o administrativa.
_Evitar_: base de datos destino, lago de datos

**Lakehouse universitario**:
Espacio de datos común que conserva información analítica y objetos compartidos por la plataforma.
_Evitar_: data lake, repositorio de archivos

**Bucket**:
Contenedor lógico dentro del lakehouse para agrupar objetos bajo una política y propósito comunes.
_Evitar_: carpeta, directorio

**Dataset**:
Conjunto identificable de datos con significado, procedencia y responsable definidos.
_Evitar_: tabla suelta, archivo suelto

## Descubrimiento y gobierno

**Federación de datos**:
Consulta unificada de datos que permanecen en sus sistemas de origen o almacenamiento asignado.
_Evitar_: copia centralizada, migración de datos

**Catálogo de datos**:
Inventario consultable de datasets, servicios y sus metadatos de negocio y técnicos.
_Evitar_: listado de tablas, diccionario aislado

**Metadato**:
Información que describe el significado, estructura, procedencia, calidad o responsable de un activo de datos.
_Evitar_: dato de negocio

**Ingesta de metadatos**:
Proceso programable que extrae metadatos técnicos desde una fuente y los registra en el catálogo de datos sin modificar la fuente.
_Evitar_: carga de datos, sincronización de datos operativos

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
