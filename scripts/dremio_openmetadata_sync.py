"""Synchronize Dremio VDS lineage and usage into OpenMetadata.

This is deliberately a custom integration: OpenMetadata 1.3.1 has no native
Dremio connector. It uses only Dremio's REST API, the OpenMetadata REST API,
and the existing ingestion-bot JWT stored in the local OpenMetadata database.
"""

import datetime as dt
import os
import sys
import time

import psycopg2
import requests


TARGET_FQN = "Dremio_Federation.Dremio.University_Lab.Student_360"
SOURCE_FQNS = (
    "SIS_MSSQL.sis_db.sis.students",
    "SIS_MSSQL.sis_db.sis.enrollments",
    "Moodle_Postgres.moodle_db.moodle.users",
    "ERPNext_Postgres.erpnext_db.erp.student_invoices",
)


def om_token():
    with psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname="openmetadata_db",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    ) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT json #>> '{authenticationMechanism,config,JWTToken}' "
            "FROM user_entity WHERE name = 'ingestion-bot'"
        )
        return cursor.fetchone()[0]


def dremio_session():
    session = requests.Session()
    response = session.post(
        f"{os.environ['DREMIO_HOST']}/apiv2/login",
        json={"userName": os.environ["DREMIO_USERNAME"], "password": os.environ["DREMIO_PASSWORD"]},
        timeout=30,
    )
    response.raise_for_status()
    session.headers["Authorization"] = f"Bearer {response.json()['token']}"
    return session


def om_session():
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {om_token()}"
    session.headers["Content-Type"] = "application/json"
    return session


def get_json(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def post_if_missing(session, endpoint, payload):
    response = session.post(endpoint, json=payload, timeout=30)
    if response.status_code == 409:
        return None
    response.raise_for_status()
    return response.json()


def get_vds(dremio):
    """Resolve by path so a recreated Dremio instance can assign a new UUID."""
    root = get_json(dremio, f"{os.environ['DREMIO_HOST']}/api/v3/catalog")["data"]
    space = next(item for item in root if item.get("path") == ["University_Lab"])
    children = get_json(dremio, f"{os.environ['DREMIO_HOST']}/api/v3/catalog/{space['id']}")["children"]
    vds = next(item for item in children if item.get("path") == ["University_Lab", "Student_360"])
    return get_json(dremio, f"{os.environ['DREMIO_HOST']}/api/v3/catalog/{vds['id']}")


def ensure_catalog(om, vds):
    api = os.environ["OPENMETADATA_API_URL"]
    admin = get_json(om, f"{api}/users/name/admin")
    owner = {"id": admin["id"], "type": "user"}
    post_if_missing(om, f"{api}/services/databaseServices", {
        "name": "Dremio_Federation", "displayName": "Dremio Federation",
        "serviceType": "CustomDatabase", "owner": owner,
        "description": "Capa de federación Dremio sincronizada mediante su API.",
        "connection": {"config": {"type": "CustomDatabase", "connectionOptions": {"endpoint": os.environ["DREMIO_HOST"]}}},
    })
    post_if_missing(om, f"{api}/databases", {"name": "Dremio", "service": "Dremio_Federation", "owner": owner, "description": "Catálogo lógico de Dremio."})
    post_if_missing(om, f"{api}/databaseSchemas", {"name": "University_Lab", "database": "Dremio_Federation.Dremio", "owner": owner, "description": "Espacio de vistas federadas universitarias."})
    type_map = {"VARCHAR": "VARCHAR", "DATE": "DATE", "DECIMAL": "DECIMAL", "BIGINT": "BIGINT", "INTEGER": "INT"}
    columns = []
    for position, field in enumerate(vds["fields"], 1):
        source_type = field["type"]["name"]
        column = {"name": field["name"], "dataType": type_map.get(source_type, "VARCHAR"), "ordinalPosition": position, "description": f"Columna {field['name']} publicada por la vista federada Student_360."}
        if column["dataType"] == "VARCHAR":
            column["dataLength"] = 255
        if column["dataType"] == "DECIMAL":
            column.update({"precision": field["type"].get("precision", 38), "scale": field["type"].get("scale", 0)})
        columns.append(column)
    post_if_missing(om, f"{api}/tables", {"name": "Student_360", "displayName": "Student 360", "databaseSchema": "Dremio_Federation.Dremio.University_Lab", "tableType": "View", "owner": owner, "description": "Vista virtual que consolida identidad académica, matrícula, Moodle y facturación por estudiante.", "columns": columns, "viewDefinition": vds["sql"], "sourceUrl": os.environ["DREMIO_HOST"]})


def publish_lineage():
    dremio = dremio_session()
    vds = get_vds(dremio)
    if not vds.get("sql"):
        raise RuntimeError("Dremio did not return the SQL definition for Student_360")

    om = om_session()
    ensure_catalog(om, vds)
    if not all(part.split(".")[0] in vds["sql"] for part in SOURCE_FQNS):
        raise RuntimeError("Student_360 no coincide con las fuentes de lineage aprobadas")
    target = get_json(om, f"{os.environ['OPENMETADATA_API_URL']}/tables/name/{TARGET_FQN}")
    for source_fqn in SOURCE_FQNS:
        source = get_json(om, f"{os.environ['OPENMETADATA_API_URL']}/tables/name/{source_fqn}")
        response = om.put(
            f"{os.environ['OPENMETADATA_API_URL']}/lineage",
            json={
                "edge": {
                    "fromEntity": {"id": source["id"], "type": "table"},
                    "toEntity": {"id": target["id"], "type": "table"},
                }
            },
            timeout=30,
        )
        response.raise_for_status()


def run_sql(dremio, sql):
    response = dremio.post(f"{os.environ['DREMIO_HOST']}/api/v3/sql", json={"sql": sql}, timeout=30)
    response.raise_for_status()
    job_id = response.json()["id"]
    for _ in range(30):
        job = get_json(dremio, f"{os.environ['DREMIO_HOST']}/api/v3/job/{job_id}")
        if job.get("jobState") == "COMPLETED":
            return get_json(dremio, f"{os.environ['DREMIO_HOST']}/api/v3/job/{job_id}/results")
        if job.get("jobState") in {"FAILED", "CANCELED"}:
            raise RuntimeError(f"Dremio usage query failed: {job}")
        time.sleep(2)
    raise TimeoutError("Timed out waiting for the Dremio usage query")


def publish_usage():
    date = dt.datetime.now(dt.timezone(dt.timedelta(hours=-6))).date().isoformat()
    dremio = dremio_session()
    result = run_sql(
        dremio,
        "SELECT COUNT(*) AS usage_count FROM sys.jobs_recent "
        f"WHERE TO_CHAR(submitted_ts, 'YYYY-MM-DD') = '{date}' "
        "AND query LIKE '%\"University_Lab\".\"Student_360\"%' AND query_type = 'REST'",
    )
    source_count = int(result["rows"][0]["usage_count"])

    om = om_session()
    ensure_catalog(om, get_vds(dremio))
    table = get_json(om, f"{os.environ['OPENMETADATA_API_URL']}/tables/name/{TARGET_FQN}")
    current = get_json(om, f"{os.environ['OPENMETADATA_API_URL']}/usage/table/{table['id']}")
    current_count = next((entry["dailyStats"]["count"] for entry in current["usage"] if entry["date"] == date), 0)
    delta = source_count - current_count
    if delta > 0:
        response = om.put(
            f"{os.environ['OPENMETADATA_API_URL']}/usage/table/{table['id']}",
            json={"date": date, "count": delta},
            timeout=30,
        )
        response.raise_for_status()


if __name__ == "__main__":
    operation = sys.argv[1] if len(sys.argv) == 2 else ""
    if operation == "bootstrap":
        dremio = dremio_session()
        ensure_catalog(om_session(), get_vds(dremio))
    elif operation == "lineage":
        publish_lineage()
    elif operation == "usage":
        publish_usage()
    else:
        raise SystemExit("usage: dremio_openmetadata_sync.py {bootstrap|lineage|usage}")
