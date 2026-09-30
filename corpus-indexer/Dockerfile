FROM python:3.12-slim
# Indexador del corpus documental: embeddings locales (CPU) + OpenSearch k-NN + MinIO.
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir \
    sentence-transformers==3.0.1 \
    opensearch-py==2.4.2 \
    boto3==1.34.144
COPY load_corpus.py /app/load_corpus.py
WORKDIR /app
