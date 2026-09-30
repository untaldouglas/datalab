# Guion replicable: Metabase conectado a Dremio (capa oro)

Guion paso a paso para reproducir la capa BI en cualquier reinstalación del laboratorio. Todo es reproducible con `make` salvo los pasos de primer alta de Metabase, que también se pueden automatizar con su API (se anota el comando equivalente).

## 0. Requisitos previos

- Stack levantado: `make up` y `make check` en verde.
- Vistas medallion creadas: `make demo-views`.
- Catálogo OpenMetadata al día: `make metadata-dremio-sync`.

## 1. Levantar Metabase

```bash
make metabase        # http://localhost:3030 (solo localhost)
```

La imagen se construye desde `metabase/Dockerfile`, que hace dos cosas obligatorias:

1. Instala el driver comunitario [Arrow Flight SQL](https://github.com/J0hnG4lt/metabase-flightsql-driver) (`arrow-flight-sql.metabase-driver.jar`, versión 0.6.1 fijada) en `/plugins/`, con permisos `644` (sin `chmod` Metabase no lo carga).
2. Define `JAVA_OPTS` con `--add-opens` y `--sun-misc-unsafe-memory-access=allow`: el JDK 25 de la imagen rompe el asignador de memoria de Arrow sin esa bandera.

> **Por qué Flight SQL y no el puerto 31010:** Dremio OSS no expone protocolo PostgreSQL en `31010`; ese puerto es su RPC propietario. La vía soportada de Metabase a Dremio OSS es Arrow Flight SQL en el puerto `32010`. Confirmado con pruebas reales: un intento con driver PostgreSQL falla con `EOFException` en el handshake.

## 2. Primer alta (solo la primera vez)

Abrir `http://localhost:3030` y crear la cuenta administradora local de desarrollo. Automatizable por API:

```bash
SETUP_TOKEN=$(curl -s http://localhost:3030/api/session/properties | jq -r '."setup-token"')
curl -s -X POST http://localhost:3030/api/setup -H 'Content-Type: application/json' -d '{
  "token": "'"$SETUP_TOKEN"'",
  "user": {"first_name": "Douglas", "last_name": "Admin", "email": "admin@datalab.local",
           "password": "<contraseña de desarrollo>", "site_name": "Datalab UJMD"},
  "prefs": {"site_name": "Datalab UJMD", "site_locale": "es", "allow_tracking": false}
}'
```

## 3. Usuario de solo consulta en Dremio

No uses la cuenta administradora de Dremio para BI. Crea un usuario local dedicado (con sesión de administrador de Dremio):

```bash
PUT /apiv2/user/metabase_reader
{"userName": "metabase_reader", "password": "<contraseña de desarrollo>",
 "fullName": "Metabase Reader", "email": "metabase@datalab.local", "active": true}
```

Verifica con el propio usuario: `POST /apiv2/login` y una consulta `SELECT COUNT(*) FROM "Gold_Rectoria"."Rectoral_Academic_Summary"`.

## 4. Conectar la base en Metabase

Admin → Bases de datos → Add database, motor **Arrow Flight SQL**:

| Campo | Valor |
| --- | --- |
| Host | `dremio` |
| Port | `32010` |
| Username / Password | `metabase_reader` |
| Use Encryption | **Off** (sin TLS en el laboratorio local) |
| Schema filters | Patterns: `Gold_Rectoria,Gold_Decanatos,Gold_VR_Financiera` |

Automatizable: `POST /api/database` con `engine: "arrow-flight-sql"` y esos `details`. Después de crearla, espera `initial_sync_status = complete`.

## 5. Colección, preguntas y tablero

Los dashboards se construyen **solo sobre datasets de los espacios `Gold_*`**. La colección de Rectoría creada en esta sesión sirve de plantilla:

1. Colección `Rectoría (Gold)`.
2. Pregunta nativa: `SELECT faculty, eligible_students, participating_students, participation_pct FROM "Gold_Rectoria"."Rectoral_Academic_Summary" ORDER BY faculty` (gráfica de barras).
3. Pregunta nativa: `SELECT academic_semester, payment_status, invoices, billed_amount, outstanding_amount FROM "Gold_Rectoria"."Rectoral_Financial_Summary" ORDER BY academic_semester`.
4. Tablero `Tablero Rectoría` con ambas tarjetas: http://localhost:3030/dashboard/1

Nuevas audiencias = nuevo espacio `Gold_<Audiencia>` + colección en Metabase con el mismo patrón.

## 6. Verificación después de replicar

1. `curl http://localhost:3030/api/health` → `{"status":"ok"}`.
2. En Metabase, la base `Dremio (Gold)` debe mostrar `initial_sync_status: complete`.
3. Las dos preguntas del tablero devuelven filas (los agregados demo tienen 1 fila cada uno con la seed actual).
4. `make metadata-verify` sigue en PASS: Metabase no altera el catálogo.

## Límites de gobierno (honestos)

- El filtro de esquemas limita el **descubrimiento** inicial y las resincronizaciones; las tablas ya sincronizadas permanecen visibles hasta eliminarse manualmente.
- En Dremio OSS no hay grants por esquema verificables, así que `metabase_reader` puede leer técnicamente cualquier dataset. El control duro de consumo externo sigue siendo el gateway de consultas aprobadas ([ADR 0002](adr/0002-dremio-oss-consumer-access-gate.md)); la restricción "Metabase solo `Gold_*`" es disciplina operativa documentada, reforzable en producción con Dremio Enterprise/Cloud ([ADR 0003](adr/0003-dremio-medallion-audience-spaces.md)).
- Metabase usa base H2 embebida en su volumen `metabase_data`: suficiente para la POC, migrar a PostgreSQL si la demo crece.
