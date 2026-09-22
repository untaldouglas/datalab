# Guía de contribución

## Antes de empezar

1. Revisa los issues existentes y describe el problema o propuesta antes de cambios grandes.
2. Mantén los cambios acotados a una intención clara.
3. No añadas secretos, archivos `.env`, volcados de bases de datos ni volúmenes Docker al repositorio.

## Flujo propuesto

```bash
make config
make up
make check
```

Para cada cambio:

1. Si se introduce, modifica o aclara un concepto de la plataforma, actualiza [CONTEXT.md](CONTEXT.md) en el mismo cambio. Usa el término canónico y registra sinónimos desaconsejados bajo `_Evitar_`.
2. Actualiza la documentación que afecte a instalación, operación o seguridad.
3. Ejecuta `make config`.
4. Ejecuta `make check` si el stack está disponible.
5. En el pull request, explica el cambio, cómo se verificó y cualquier impacto en datos, credenciales o vocabulario del dominio.

## Convenciones

- Usa nombres de servicios y puertos coherentes con `docker-compose.yml`.
- Fija versiones de imágenes cuando la reproducibilidad o la seguridad lo requieran.
- Añade healthchecks a los servicios que sean dependencia de otros.
- Nunca uses credenciales de producción en archivos versionados.

## Reportes de errores

Incluye la versión de Docker/Compose, el sistema operativo, el objetivo de Make ejecutado, el resultado de `make ps` y registros relevantes sin secretos.
