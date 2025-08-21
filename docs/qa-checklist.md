# Local QA Checklist

Follow these steps to sanity-check the stack and expected metrics/outputs.

## 1) Start stack
- Command: `make integration-up`
- Verify: `curl http://localhost:8080/healthz` returns `{"status":"ok"}`.

## 2) Seed demo DB
- Command: `docker exec mssql /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P 'Your_strong_Pa55' -Q "CREATE DATABASE demo; USE demo; CREATE TABLE T(Id INT, Phone NVARCHAR(32)); CREATE PROC dbo.Upd @Id INT, @Phone NVARCHAR(32) AS BEGIN UPDATE T SET Phone=@Phone WHERE Id=@Id; END; INSERT INTO T VALUES (1,'0701234567');"`

## 3) Send traffic via proxy
- Command: `docker exec mssql /opt/mssql-tools/bin/sqlcmd -S proxy,61433 -U sa -P 'Your_strong_Pa55' -Q "USE demo; SELECT COUNT(*) FROM T; EXEC dbo.Upd 1, '0707654321'; SELECT TOP 1 Phone FROM T WHERE Id=1;"`
- Expected: `rpc_seen` increases in metrics; with a phone autocorrect rule loaded, `rpc_autocorrect_inplace` increases.

## 4) Check metrics & dashboards
- JSON: `curl -s http://localhost:8080/metrics | jq .`
- Dry‑run JSON: `DAY=$(date -u +%F); curl -s "http://localhost:8080/dryrun.json?date=$DAY" | jq .`
- HTML: open `http://localhost:8080/metrics.html`, `http://localhost:8080/dryrun.html`.

## 5) Reports
- Run: `python scripts/generate_daily_report.py && python scripts/generate_dryrun_report.py && python scripts/llm_summarize_profiles.py`
- Expected: files under `reports/` for today (`report-…`, `dryrun-…`, `llm-summary-…`).

## 6) Tear down
- Command: `make integration-down`
