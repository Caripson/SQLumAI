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

## Enable LLM via Ollama
- The stack includes an `ollama` service. The proxy is configured with `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.2`, `LLM_ENDPOINT=http://ollama:11434`.
- First run pulls the model: `docker exec ollama ollama run llama3.2 -p "hi"`.
- Generate an LLM summary: `docker exec proxy python scripts/llm_summarize_profiles.py` (ensure profiles exist under `data/aggregations/field_profiles.json`).

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

## Manage rules via UI and API
- Minimal UI: open `http://localhost:8080/rules/ui` to browse and skapa regler. Använd testpanelen för att simulera ett beslut mot nuvarande regler.
- API exempel (CRUD):
```bash
curl -s -X POST http://localhost:8080/rules \
  -H 'Content-Type: application/json' \
  -d '{"id":"no-null-email","target":"column","selector":"dbo.Users.Email","action":"block","reason":"Email required","confidence":1.0}'
curl -s http://localhost:8080/rules | jq .
```

## XEvents setup (guided)
Hämta en färdig SQL‑session för Extended Events via API:
```bash
curl -s -X POST "http://localhost:8080/xevents/setup?mode=ring" | jq -r .sql > create_xevents.generated.sql
# Kör i SQL Server (via SSMS/sqlcmd) för att skapa/startera sessionen
```
Alternativt generera lokalt:
```bash
python scripts/setup_xevents.py > scripts/create_xevents.generated.sql
```

## Rule suggestion from natural language
Låt API föreslå en regel från klartext (ingen auto‑apply):
```bash
curl -s -X POST http://localhost:8080/rules/suggest \
  -H 'Content-Type: application/json' \
  -d '{"text":"Email måste vara obligatorisk"}' | jq .
```

## Simulation with example events
Kör en torrkörning på exempeldata:
```bash
make simulate INPUT=examples/events-sample.jsonl
```
Se även fler detaljer i `docs/examples.md`.

## SELECT‑analys och drift
- `scripts/aggregate_profiles.py` skriver även statistik för SELECT (t.ex. antal `SELECT *` per tabell). `scripts/generate_daily_report.py` tar med en sektion “SELECT Analysis”.
- Enkel null‑drift rapporteras om en tidigare snapshot finns i `data/aggregations/field_profiles.prev.json`.

## Secrets
Sätt `SECRET_PROVIDER=env|file` och läs hemligheter via `src/runtime/secrets.py`. Exempel (file):
```bash
export SECRET_PROVIDER=file
export SQL_PASSWORD_FILE=/run/secrets/sql_password
```
