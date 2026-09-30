# Gate de acceso de consumo con Dremio OSS

**Estado: aceptada e implementada para la POC local.**

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

Para esta POC se escogió la segunda alternativa. `metrics-gateway` se publica únicamente en `127.0.0.1:8092`, no recibe SQL y sólo ejecuta consultas fijas contra `Rectoral_Academic_Summary` y `Rectoral_Financial_Summary`. Sus filtros se validan contra valores de negocio permitidos y registra solicitudes y rechazos como eventos JSON. Se autentica con el usuario local no administrativo `metrics_gateway`, provisionado de forma idempotente por `make gateway`; no recibe la credencial administradora.

## Criterio de salida del gate

La solución elegida debe demostrar que:

- puede recuperar ambos resúmenes rectorales por el punto de consumo;
- rechaza SQL, rutas, métricas y filtros no autorizados, por lo que no expone `Eligible_Student_Activity`, `Academic_Activity_Events`, `Student_360` ni sources transaccionales;
- no ofrece operaciones de creación, modificación o borrado;
- conserva evidencia de solicitud, métrica, filtros y número de filas. La fecha de corte pertenece a cada fila retornada.

## Consecuencias

Las vistas y métricas pueden seguir siendo verificadas y catalogadas. Dashboards y agentes deberán conectarse sólo al gateway, nunca a Dremio con la credencial administrativa. Este control es suficiente para la demostración local; la cuenta no administrativa reduce el impacto de una falla del gateway, pero OSS aún no permite limitarla por vista. Producción requiere identidad de servicio, gestión de secretos, autenticación de consumidores y RBAC nativo.
