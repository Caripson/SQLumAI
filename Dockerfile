FROM python:3.11-slim

# Project version for labels; override with --build-arg VERSION=x.y.z
ARG VERSION=0.1.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# OCI image labels
LABEL org.opencontainers.image.title="SQLumAI" \
      org.opencontainers.image.description="AI-powered SQL Server proxy and data quality assistant" \
      org.opencontainers.image.version=${VERSION} \
      org.opencontainers.image.authors="Johan Caripson" \
      org.opencontainers.image.vendor="Johan Caripson" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Caripson/SQLumAI"

ENV SQLUMAI_VERSION=${VERSION} \
    PROXY_LISTEN_ADDR=0.0.0.0 \
    PROXY_LISTEN_PORT=61433 \
    SQL_HOST=mssql \
    SQL_PORT=1433 \
    ENABLE_API=true \
    API_HOST=0.0.0.0 \
    API_PORT=8080

EXPOSE 61433 8080

CMD ["python", "-m", "src.main"]
