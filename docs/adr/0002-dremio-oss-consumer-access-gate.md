# Gate de acceso de consumo con Dremio OSS

**Estado: aceptada para la POC local.**

## Contexto

Las vistas `Rectoral_Academic_Summary` y `Rectoral_Financial_Summary` son los únicos datasets agregados previstos para dashboards y agentes. Las vistas `Eligible_Student_Activity` y `Academic_Activity_Events` contienen identificadores técnicos y se usan sólo para cálculo interno.

La POC ejecuta la imagen `dremio/dremio-oss`. El 30 de septiembre de 2026 se verificó localmente que el catálogo resuelve las vistas, pero `GET /api/v3/catalog/{id}/grants` responde `404`. Por tanto, no se dispone de un mecanismo verificable de privilegios por vista en esta instalación. Crear una cuenta lectora sin poder probar esa restricción sería un control aparente, no un control efectivo.

## Decisión

1. No se conectarán dashboards, Langflow ni Hermes a Dremio con la cuenta administradora actual.
2. No se creará una cuenta de consumo hasta contar con privilegios por vista comprobables.
3. Las capas con identificadores se mantienen internas y no forman parte de ningún conector de negocio o IA.
4. Para habilitar consumo se escogerá una de estas alternativas:
   - Dremio Enterprise o Cloud con `SELECT` exclusivo sobre los dos resúmenes agregados; o
   - un gateway de consultas de solo lectura, con lista permitida de vistas, identidad de servicio propia y registro de cada consulta.

## Criterio de salida del gate

La solución elegida debe demostrar con una identidad no administrativa que:

- puede ejecutar `SELECT` en ambos resúmenes rectorales;
- recibe denegación al consultar `Eligible_Student_Activity`, `Academic_Activity_Events`, `Student_360` y los sources transaccionales;
- no puede crear, modificar ni borrar vistas;
- conserva evidencia de identidad, vista consultada, fecha de corte y filtros.

## Consecuencias

Las vistas y métricas pueden seguir siendo verificadas y catalogadas. La publicación de dashboards y la conexión de agentes quedan bloqueadas hasta superar este gate; no se presentan como consumo gobernado antes de ello.
