# Política de seguridad

## Alcance

Este repositorio describe un entorno local de demostración. Las contraseñas incluidas son solo valores de desarrollo y deben sustituirse antes de cualquier uso compartido o despliegue.

## Reportar una vulnerabilidad

No publiques vulnerabilidades, secretos ni datos personales en issues públicos. Contacta de forma privada a las personas mantenedoras del repositorio y proporciona:

- descripción e impacto;
- pasos reproducibles;
- versión de las imágenes afectadas;
- una propuesta de mitigación, si existe.

## Recomendaciones mínimas antes de producción

- Mover credenciales a un gestor de secretos.
- Eliminar las exposiciones de puertos innecesarias.
- Habilitar autenticación y TLS, especialmente en OpenSearch y bases de datos.
- Sustituir las imágenes con etiqueta `latest` por versiones fijadas y revisadas.
- Aplicar copias de seguridad, monitorización y un control de acceso de red.
