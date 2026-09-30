#!/usr/bin/env python3
"""Punto de entrada del asistente IA (entregable 6).

Dos herramientas separadas y nada más:
- GET /api/v1/assistant/structured?metric=academic|financial[&filtros]
    Delega en el gateway de métricas aprobadas (única vía SQL; no consulta
    Dremio directamente y no acepta SQL).
- GET /api/v1/assistant/document?q=<pregunta>
    Búsqueda vectorial k-NN sobre el corpus documental indexado. Devuelve
    fragmentos con cita (documento, título, fecha, clasificación) o declara
    sin evidencia suficiente.
- GET /health
Toda otra ruta se rechaza. Cada consulta o rechazo se audita como evento JSON.
"""
import json
import os
import time
import urllib.parse
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://metrics-gateway:8090")
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "opensearch")
MIN_SCORE = 0.60  # puntaje mínimo (cosinesimil normalizado) para aceptar evidencia

_cache = {"model": None}


def get_model():
    if _cache["model"] is None:
        from sentence_transformers import SentenceTransformer
        _cache["model"] = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _cache["model"]


def knn_search(query, k=3):
    from opensearchpy import OpenSearch
    client = OpenSearch(hosts=[{"host": OPENSEARCH_HOST, "port": 9200}], use_ssl=False, verify_certs=False)
    vector = get_model().encode(query).tolist()
    body = {
        "size": k,
        "query": {"knn": {"embedding": {"vector": vector, "k": k}}},
        "_source": ["document", "title", "source", "date", "classification", "text"],
    }
    return client.search(index="corpus_chunks", body=body)["hits"]["hits"]


def format_document_answer(hits):
    """Convierte hits k-NN en respuesta citada; declara sin evidencia si no alcanza."""
    accepted = [h for h in hits if h["_score"] >= MIN_SCORE]
    if not accepted:
        return {"evidence": "insufficient", "citations": [],
                "message": "No hay evidencia suficiente en el corpus autorizado para responder esa pregunta."}
    citations = [{
        "score": round(h["_score"], 3),
        "document": h["_source"]["document"],
        "title": h["_source"]["title"],
        "source": h["_source"]["source"],
        "date": h["_source"]["date"],
        "classification": h["_source"]["classification"],
        "excerpt": h["_source"]["text"],
    } for h in accepted]
    return {"evidence": "sufficient", "citations": citations}


def fetch_structured(metric, query_string):
    """Reenvía la consulta al gateway de métricas aprobadas; él valida filtros."""
    url = f"{GATEWAY_URL}/api/v1/metrics/{urllib.parse.quote(metric)}"
    if query_string:
        url += f"?{query_string}"
    request = Request(url)
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response), response.status
    except HTTPError as error:
        return json.load(error), error.code


def audit(event, request_id, **fields):
    print(json.dumps({"event": event, "request_id": request_id, **fields}, ensure_ascii=False), flush=True)


class AssistantHandler(BaseHTTPRequestHandler):
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
        request_id = str(uuid.uuid4())
        if parsed.path == "/health":
            try:
                payload, status = fetch_structured("academic", "")
                self.respond(HTTPStatus.OK, {"status": "ok", "gateway": payload.get("metric") == "academic"})
            except Exception:
                self.respond(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unavailable"})
            return
        if parsed.path == "/api/v1/assistant/structured":
            params = parse_qs(parsed.query)
            metric = (params.pop("metric", [""])[0]).strip()
            if metric not in {"academic", "financial"}:
                audit("assistant_rejected", request_id, route="structured", reason="metrica_no_autorizada", metric=metric)
                self.respond(HTTPStatus.BAD_REQUEST, {"error": "Métrica no autorizada.", "request_id": request_id})
                return
            query_string = urllib.parse.urlencode({k: v[0] for k, v in params.items()})
            try:
                payload, status = fetch_structured(metric, query_string)
            except (HTTPError, URLError, TimeoutError) as error:
                audit("assistant_failed", request_id, route="structured", metric=metric, error=str(error))
                self.respond(HTTPStatus.BAD_GATEWAY, {"error": "No se pudo obtener la métrica aprobada.", "request_id": request_id})
                return
            audit("assistant_structured", request_id, metric=metric, gateway_status=status)
            self.respond(status, {"request_id": request_id, **payload})
            return
        if parsed.path == "/api/v1/assistant/document":
            params = parse_qs(parsed.query)
            question = params.get("q", [""])[0].strip()
            if not question:
                audit("assistant_rejected", request_id, route="document", reason="pregunta_vacia")
                self.respond(HTTPStatus.BAD_REQUEST, {"error": "Pregunta vacía.", "request_id": request_id})
                return
            try:
                answer = format_document_answer(knn_search(question))
            except Exception as error:
                audit("assistant_failed", request_id, route="document", error=str(error))
                self.respond(HTTPStatus.BAD_GATEWAY, {"error": "No se pudo consultar el corpus.", "request_id": request_id})
                return
            audit("assistant_document", request_id, question=question, evidence=answer["evidence"], citations=len(answer["citations"]))
            self.respond(HTTPStatus.OK, {"request_id": request_id, **answer})
            return
        audit("assistant_rejected", request_id, route=str(parsed.path), reason="ruta_no_autorizada")
        self.respond(HTTPStatus.NOT_FOUND, {"error": "Ruta no autorizada.", "request_id": request_id})


def main():
    port = int(os.environ.get("ASSISTANT_PORT", "8090"))
    ThreadingHTTPServer(("0.0.0.0", port), AssistantHandler).serve_forever()


if __name__ == "__main__":
    main()
