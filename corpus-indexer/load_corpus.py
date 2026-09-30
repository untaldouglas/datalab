#!/usr/bin/env python3
"""Carga el corpus documental a MinIO y lo indexa en OpenSearch con embeddings.

- Origen de verdad: archivos markdown versionados en /corpus (frontmatter con
  source, date, classification, audience).
- MinIO bucket `openrag-docs` recibe el documento íntegro (almacenamiento).
- OpenSearch índice `corpus_chunks`: búsqueda léxica + vectorial (k-NN, 384 dims,
  modelo paraphrase-multilingual-MiniLM-L12-v2). Idempotente: recrea el índice.
"""
import datetime as dt
import hashlib
import os
import re

import boto3
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
INDEX = "corpus_chunks"
CHUNK_CHARS = 700
CHUNK_OVERLAP = 120
REQUIRED_FIELDS = {"title", "source", "date", "classification", "audience"}
CLASSIFICATIONS = {"Internal", "Confidential", "Restricted"}


def parse_frontmatter(path):
    text = open(path, encoding="utf-8").read()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path}: falta frontmatter")
    header = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            header[key.strip()] = value.strip()
    missing = REQUIRED_FIELDS - header.keys()
    if missing:
        raise ValueError(f"{path}: faltan campos {missing}")
    if header["classification"] not in CLASSIFICATIONS:
        raise ValueError(f"{path}: clasificación inválida {header['classification']}")
    dt.date.fromisoformat(header["date"])
    return header, match.group(2).strip()


def chunk_text(text):
    chunks = []
    start = 0
    while start < len(text):
        piece = text[start:start + CHUNK_CHARS].strip()
        if piece:
            chunks.append(piece)
        start += CHUNK_CHARS - CHUNK_OVERLAP
    return chunks


def minio_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("MINIO_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.environ["MINIO_USER"],
        aws_secret_access_key=os.environ["MINIO_PASSWORD"],
        region_name="us-east-1",
    )


def os_client():
    # El stack local deshabilita el plugin de seguridad de OpenSearch.
    return OpenSearch(
        hosts=[{"host": os.environ.get("OPENSEARCH_HOST", "opensearch"), "port": 9200}],
        use_ssl=False, verify_certs=False,
    )


def main():
    corpus_dir = os.environ.get("CORPUS_DIR", "/corpus")
    files = sorted(f for f in os.listdir(corpus_dir) if f.endswith(".md"))
    if not files:
        raise SystemExit("sin documentos en el corpus")

    m = minio_client()
    try:
        m.head_bucket(Bucket="openrag-docs")
    except m.exceptions.ClientError:
        m.create_bucket(Bucket="openrag-docs")

    os_client().indices.delete(index=INDEX, ignore=[400, 404])
    os_client().indices.create(index=INDEX, body={
        "settings": {"index": {"knn": True}},
        "mappings": {"properties": {
            "text": {"type": "text"},
            "document": {"type": "keyword"},
            "title": {"type": "keyword"},
            "source": {"type": "keyword"},
            "date": {"type": "date"},
            "classification": {"type": "keyword"},
            "audience": {"type": "keyword"},
            "chunk": {"type": "integer"},
            "embedding": {
                "type": "knn_vector", "dimension": EMBEDDING_DIM,
                "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "nmslib"},
            },
        }},
    })

    model = SentenceTransformer(MODEL_NAME)
    total = 0
    for name in files:
        path = os.path.join(corpus_dir, name)
        header, body = parse_frontmatter(path)
        doc_id = hashlib.sha1(name.encode()).hexdigest()[:12]
        m.put_object(Bucket="openrag-docs", Key=f"corpus/{name}", Body=open(path, "rb").read())
        for i, piece in enumerate(chunk_text(body)):
            vector = model.encode(piece).tolist()
            os_client().index(index=INDEX, body={
                "text": piece, "document": name, "title": header["title"],
                "source": header["source"], "date": header["date"],
                "classification": header["classification"], "audience": header["audience"],
                "chunk": i, "embedding": vector,
            })
            total += 1
        print(f"{name}: {len(chunk_text(body))} fragmentos, objeto subido a s3://openrag-docs/corpus/{name}")
    print(f"Indexados {total} fragmentos de {len(files)} documentos en {INDEX} (vectorial {EMBEDDING_DIM}d).")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--search":
        query = os.environ.get("QUERY", "")
        if not query:
            raise SystemExit("uso: QUERY='pregunta' load_corpus.py --search")
        model = SentenceTransformer(MODEL_NAME)
        vector = model.encode(query).tolist()
        result = os_client().search(index=INDEX, body={
            "size": 3,
            "query": {"knn": {"embedding": {"vector": vector, "k": 3}}},
            "_source": ["document", "title", "source", "date", "classification", "text"],
        })
        for hit in result["hits"]["hits"]:
            src = hit["_source"]
            print(f"[{hit['_score']:.3f}] {src['title']} ({src['document']}, {src['date']}, {src['classification']})")
            print(f"  {src['text'][:220]}...")
        raise SystemExit(0)

    main()
