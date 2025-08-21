FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PROXY_LISTEN_ADDR=0.0.0.0 \
    PROXY_LISTEN_PORT=61433 \
    SQL_HOST=mssql \
    SQL_PORT=1433 \
    ENABLE_API=true \
    API_HOST=0.0.0.0 \
    API_PORT=8080

EXPOSE 61433 8080

CMD ["python", "-m", "src.main"]

