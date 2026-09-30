FROM python:3.12-alpine

WORKDIR /app
COPY app.py /app/app.py

USER 65534:65534
EXPOSE 8090
CMD ["python", "/app/app.py"]
