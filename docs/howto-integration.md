# How-To: Run Integration Stack Locally

This guide shows how to start SQL Server + proxy, send a few queries, and verify metrics.

## Prerequisites
- Docker and Docker Compose
- Port 1433 (SQL Server), 61433 (proxy), 8080 (API) available

## Start the stack
```bash
docker compose up -d --build
curl http://localhost:8080/healthz  # should return {"status":"ok"}
```

The proxy listens on `localhost:61433`; the API is at `http://localhost:8080`.

## Create sample DB objects
Use the SQL Server container’s `sqlcmd`:
```bash
docker exec mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P 'Your_strong_Pa55' -Q "CREATE DATABASE demo; USE demo; CREATE TABLE T(Id INT, Phone NVARCHAR(32)); CREATE PROC dbo.Upd @Id INT, @Phone NVARCHAR(32) AS BEGIN UPDATE T SET Phone=@Phone WHERE Id=@Id; END; INSERT INTO T VALUES (1,'0701234567');"
```

## Send traffic via the proxy
```bash
# Select and call the stored proc through the proxy (service name 'proxy' inside compose network)
docker exec mssql /opt/mssql-tools/bin/sqlcmd -S proxy,61433 -U sa -P 'Your_strong_Pa55' -Q "USE demo; SELECT COUNT(*) FROM T; EXEC dbo.Upd 1, '0707654321'; SELECT TOP 1 Phone FROM T WHERE Id=1;"
```

## Verify metrics
```bash
curl -s http://localhost:8080/metrics | jq .
# Expect keys like: rpc_seen, allowed/autocorrect_suggested/blocks etc.
```

To see dry‑run aggregates for today:
```bash
DAY=$(date -u +%F)
curl -s "http://localhost:8080/dryrun.json?date=$DAY" | jq .
```

## Toggle enforcement
- By default, `ENFORCEMENT_MODE=log` (dry‑run, non‑blocking).
- To enforce locally, either:
  - Set `ENFORCEMENT_MODE=enforce` in `.env` and restart, or
  - Use an override file: `docker compose -f compose.yml -f compose.ci.yml up -d` (see compose.ci.yml for example settings).

Tip: Visit `http://localhost:8080/metrics.html` and `http://localhost:8080/dryrun.html` for a quick HTML view.
