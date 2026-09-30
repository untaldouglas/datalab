#!/usr/bin/env python3
"""HTTP gateway that exposes only approved aggregate Dremio queries."""
import json
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


METRICS = {
    "academic": {
        "view": '"Gold_Rectoria"."Rectoral_Academic_Summary"',
        "columns": "academic_term, faculty, academic_program, course_code, reporting_cutoff, eligible_students, participating_students, eligible_without_recent_activity, participation_pct",
        "filters": {
            "faculty": ("faculty", {"Ingeniería", "Administración", "Economía"}),
            "program": ("academic_program", {"Ingeniería de Datos", "Administración", "Economía"}),
            "course": ("course_code", {"DAT-101", "DAT-220", "ADM-210", "ECO-115"}),
        },
    },
    "financial": {
        "view": '"Gold_Rectoria"."Rectoral_Financial_Summary"',
        "columns": "academic_semester, reporting_cutoff, payment_status, invoices, billed_amount, paid_amount, outstanding_amount",
        "filters": {"status": ("payment_status", {"paid", "partial", "unpaid", "overdue"})},
    },
}


def build_metric_query(metric, supplied_filters):
    """Build one fixed query; only documented filter values may alter it."""
    if metric not in METRICS:
        raise ValueError("Métrica no autorizada.")
    definition = METRICS[metric]
    conditions = []
    for parameter, values in supplied_filters.items():
        if parameter not in definition["filters"] or len(values) != 1:
            raise ValueError("Filtro no autorizado.")
        column, allowed = definition["filters"][parameter]
        value = values[0]
        if value not in allowed:
            raise ValueError("Valor de filtro no autorizado.")
        conditions.append(f"{column} = '{value}'")
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    return f"SELECT {definition['columns']} FROM {definition['view']}{where}"


def audit(event, request_id, **fields):
    print(json.dumps({"event": event, "request_id": request_id, **fields}, ensure_ascii=False), flush=True)


class DremioClient:
    def __init__(self, host, username, password):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password

    def request_json(self, method, path, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            f"{self.host}{path}",
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
            method=method,
        )
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    def query(self, sql):
        token = self.request_json("POST", "/apiv2/login", {"userName": self.username, "password": self.password})["token"]
        job_id = self.request_json("POST", "/api/v3/sql", {"sql": sql}, token)["id"]
        for _ in range(30):
            job = self.request_json("GET", f"/api/v3/job/{job_id}", token=token)
            if job["jobState"] == "COMPLETED":
                return self.request_json("GET", f"/api/v3/job/{job_id}/results", token=token)["rows"]
            if job["jobState"] in {"FAILED", "CANCELED"}:
                raise RuntimeError("La consulta aprobada no pudo completarse.")
            time.sleep(1)
        raise TimeoutError("La consulta aprobada excedió el tiempo de espera.")


class GatewayHandler(BaseHTTPRequestHandler):
    client = None

    def log_message(self, format, *args):
        return

    def respond(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            try:
                self.client.query("SELECT 1 AS ready")
            except Exception:
                self.respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"})
            else:
                self.respond(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/":
            page = ("<!doctype html><title>Gateway institucional</title>"
                    "<h1>Gateway institucional</h1><p>Consultas agregadas autorizadas.</p>"
                    "<button onclick=\"load('academic')\">Resumen académico</button> "
                    "<button onclick=\"load('financial')\">Resumen financiero</button>"
                    "<pre id=result></pre><script>async function load(m){const r=await fetch('/api/v1/metrics/'+m);document.querySelector('#result').textContent=JSON.stringify(await r.json(),null,2)}</script>")
            body = page.encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        prefix = "/api/v1/metrics/"
        request_id = str(uuid.uuid4())
        if not parsed.path.startswith(prefix):
            audit("metric_rejected", request_id, reason="route_not_allowed")
            self.respond(HTTPStatus.NOT_FOUND, {"error": "Ruta no autorizada.", "request_id": request_id})
            return
        metric = parsed.path.removeprefix(prefix)
        filters = parse_qs(parsed.query, keep_blank_values=True)
        try:
            sql = build_metric_query(metric, filters)
            rows = self.client.query(sql)
        except ValueError as error:
            audit("metric_rejected", request_id, metric=metric, reason=str(error))
            self.respond(HTTPStatus.BAD_REQUEST, {"error": str(error), "request_id": request_id})
        except Exception:
            audit("metric_failed", request_id, metric=metric)
            self.respond(HTTPStatus.BAD_GATEWAY, {"error": "No se pudo obtener la métrica aprobada.", "request_id": request_id})
        else:
            audit("metric_query", request_id, metric=metric, filters=filters, row_count=len(rows))
            self.respond(HTTPStatus.OK, {"metric": metric, "rows": rows, "request_id": request_id})


def main():
    port = int(os.environ.get("GATEWAY_PORT", "8090"))
    GatewayHandler.client = DremioClient(
        os.environ["DREMIO_HOST"], os.environ["DREMIO_USERNAME"], os.environ["DREMIO_PASSWORD"]
    )
    ThreadingHTTPServer(("0.0.0.0", port), GatewayHandler).serve_forever()


if __name__ == "__main__":
    main()
