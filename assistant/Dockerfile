FROM python:3.12-slim
# Asistente IA: reutiliza el stack del corpus-indexer (embeddings locales + OpenSearch)
# y delega la ruta estructurada en el gateway de métricas aprobadas.
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    sentence-transformers==3.0.1 \
    opensearch-py==2.4.2
COPY assistant_api.py /app/assistant_api.py
WORKDIR /app
ENV ASSISTANT_PORT=8090
CMD ["python", "/app/assistant_api.py"]
