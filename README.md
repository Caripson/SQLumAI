# SQLumAI
[![CI](https://github.com/Caripson/SQLumAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Caripson/SQLumAI/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SQLumAI is an invisible, AI‑powered proxy for Microsoft SQL Server.

For non‑technical readers
- What it does: Watches data flowing to SQL Server and helps improve data quality – without slowing anything down.
- How it helps: Finds missing values, inconsistent formats (dates, phone numbers), and process gaps; proposes fixes and simpler input rules; summarizes issues daily.
- Why it’s safe: It forwards traffic transparently by default (dry‑run). You control when to enforce rules.
- Where AI fits: A local LLM turns raw events into a short list of high‑value actions and insights.

Developed by Johan Caripson.

## Quick Start
- Docker: `docker compose up` (starts SQL Server + proxy + API).
- Local: `make setup` then `make dev`.
- Tests: `make test` (and `make coverage`).

## Capabilities (MVP 1–3)
- MVP 1 – Transparent pass‑through: TCP proxy + XEvents readers (`scripts/create_xevents.sql`, `scripts/read_xevents.py`, `scripts/read_xel_files.py`), aggregation + daily reports.
- MVP 2 – Normalization + feedback: `agents/normalizers.py` (date/phone/postal/email/country/orgnr), webhook feedback, LLM summaries.
- MVP 3 – Gatekeeper: Rules API + engine, env‑gating, thresholds; optional TLS termination + TDS parsing for SQL Batch/RPC; simple column‑level autocorrect; metrics, audits, dashboards.
  - Dry‑run vs enforce: `ENFORCEMENT_MODE=log|enforce`
  - Parsers: `ENABLE_TDS_PARSER=true`, `ENABLE_SQL_TEXT_SNIFF=true`
  - LLM: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_ENDPOINT` (Ollama default), `OPENAI_API_KEY` (OpenAI-compatible)
  - Scheduler: `ENABLE_SCHEDULER`, `SCHEDULE_INTERVAL_SEC`
  - Docs overview: see `docs/mvp.md`

See `AGENTS.md` for contributor guidelines and development conventions.

## Architecture
```mermaid
flowchart LR
  subgraph Clients
    A[Apps/BI/ETL]
  end
  subgraph Proxy
    P[SQLumAI Proxy - TCP/TLS TDS]
    API[Rules API]
  end
  subgraph SQL[Microsoft SQL Server]
    XE[Extended Events: rpc_completed + sql_batch_completed]
  end
  subgraph Analysis
    R[Readers: XEvents ring/file] --> AGG[Aggregation & Profiles]
    AGG --> LLM[LLM Summaries]
    LLM --> FEED[Slack/Jira/Webhook]
  end

  A <--> P
  P <--> SQL
  XE --> R
  API --> P
```

Docs
- Browse docs in `docs/` or serve with `mkdocs serve`.
- MVPs: `docs/mvp.md`  |  Enforcement: `docs/ENFORCEMENT.md`  |  Architecture: `docs/architecture.md`
- LLM config/providers: `docs/llm-providers.md`  |  Insights: `docs/insights.md`
- Reports/Integration: `docs/howto-reports.md`, `docs/howto-integration.md`
- Metrics dashboard: `docs/metrics-dashboard.md`
- Test strategy: `docs/test-strategy.md`

## Nightly Scheduler (example)
Set these in your `.env` or environment to run the full pipeline hourly (or nightly by setting a longer interval):

```
ENABLE_SCHEDULER=true
SCHEDULE_INTERVAL_SEC=3600   # 1h; use 86400 for nightly

# SQL connection for XEvents readers
SQL_HOST=localhost
SQL_PORT=1433
SQL_USER=sa
SQL_PASSWORD=Your_strong_Pa55
SQL_DATABASE=master

# Optional: read XEL files produced by event_file target
XEL_PATH_PATTERN=C:\\ProgramData\\SQLumAI\\sqlumai_capture*.xel

# Optional: post daily summary to a webhook
FEEDBACK_WEBHOOK=
```

TLS termination for the proxy is optional. See `CERTS_README.md` for dev certs.

Metrics
- API exposes `/metrics` with simple counters: `allowed`, `autocorrect_suggested`, `blocks`.
- Dry-run report: `python scripts/generate_dryrun_report.py` writes `reports/dryrun-YYYY-MM-DD.md` (also run by scheduler).
 - Prometheus endpoint: `/metrics/prom` and Grafana dashboard via `make metrics-up`.

## License

MIT – see [LICENSE](LICENSE).

## Connection & DSN examples
- ODBC: `Driver={ODBC Driver 18 for SQL Server};Server=localhost,61433;Database=master;UID=sa;PWD=...;Encrypt=no;`
- ADO.NET: `Server=localhost,61433;Database=master;User Id=sa;Password=...;TrustServerCertificate=True;`
- JDBC: `jdbc:sqlserver://localhost:61433;databaseName=master;encrypt=false`

## XEvents cleanup (SQL)
Use the snippet below to stop and drop both sessions if needed (same logic exists in `scripts/drop_xevents.sql`).

```sql
IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture')
BEGIN
  ALTER EVENT SESSION [sqlumai_capture] ON SERVER STATE = STOP;
  DROP EVENT SESSION [sqlumai_capture] ON SERVER;
END

IF EXISTS (SELECT * FROM sys.server_event_sessions WHERE name = 'sqlumai_capture_file')
BEGIN
  ALTER EVENT SESSION [sqlumai_capture_file] ON SERVER STATE = STOP;
  DROP EVENT SESSION [sqlumai_capture_file] ON SERVER;
END
```

## Normalization & Policy examples
- Normalize (MVP 2): use `agents/normalizers.py` for dates/phones/postal/emails. Example usage:

```python
from agents.normalizers import suggest_normalizations
assert suggest_normalizations("31/12/24")["normalized"] == "2024-12-31"
```

- Policy rules (MVP 3): managed via the Rules API and persisted in `config/rules.json`.

```json
[
  {"id":"phone-autocorrect","target":"column","selector":"dbo.Customers.Phone","action":"autocorrect","reason":"Normalize SE phone","confidence":0.95},
  {"id":"no-null-email","target":"column","selector":"dbo.Users.Email","action":"block","reason":"Email required","confidence":1.0},
  {"id":"deny-test-data","target":"pattern","selector":"INSERT INTO dbo.Orders","action":"block","reason":"No test orders in prod","confidence":0.9}
]
```

API examples:

```bash
curl -s http://localhost:8080/rules | jq .
curl -s -X POST http://localhost:8080/rules \
  -H 'Content-Type: application/json' \
  -d '{"id":"no-null-email","target":"column","selector":"dbo.Users.Email","action":"block","reason":"Email required","confidence":1.0}'
```

## Användningsscenarier: BSS, Bokning, ServiceNow, CRM

Den här sektionen beskriver praktiska flöden och hur SQLumAI kan användas i olika affärssystem. Fokus är på datakvalitet, process‑luckor och hur en lokal LLM förvandlar råa händelser till få, värdefulla åtgärder och insikter – utan att skicka data externt.

### Var AI passar in
- Observabilitet: Proxy och XEvents samlar råa händelser (SQL Batch/RPC, fältvärden i framskiktet när möjligt).
- Normalisering: Regler och normalizers föreslår enkla åtgärder (t.ex. telefonformat, datum, e‑post) innan de når databasen.
- Sammanställning: Jobb profilerar fält dagligen och bygger aggregat (topplistor, null‑andelar, frekvens av felhändelser).
- LLM‑summering (lokal): En lokal modell (Ollama/llama3.2 som standard) läser profiler + händelser och producerar en kort lista över:
  - Åtgärder (”lägg till enkel validering i formulär X”, ”normalisera fält Y”, ”blockera transaktioner med mönster Z i prod”),
  - Insikter (”30% bokningar saknar e‑post i kanal A”, ”testdata i prodtabell T”, ”SLA‑risk för incidenttyp Q”).
- Feedback: Insikter kan publiceras till webhook (Slack/Jira/ServiceNow‑integration), eller bara skrivas ut i rapporter under `reports/`.

Grundprinciper:
- Lokal först: Ingen data skickas till externa LLM‑tjänster som standard. Ollama kör lokalt.
- Dry‑run som default: Proxy blockerar inte – den loggar och föreslår. Du väljer när regler ska börja gälla (enforce).
- Enkla regler: LLM föreslår, människa godkänner; regler blir tydliga i `config/rules.json` och spårbara i Git.

### BSS (Business Support System)
- Typiska problem:
  - Olikformade kunduppgifter (telefon, e‑post, adress), saknade fält vid onboarding, felaktiga organisationsnummer.
  - ”Workarounds” i CRM/BSS‑UI som leder till inkonsistenta poster i kundregister och abonnemangsdata.
- Insamling:
  - TDS‑proxy ser `INSERT/UPDATE` på tabeller som `dbo.Customers`, `dbo.Subscriptions` och RPC‑anrop för onboarding‑flöden.
  - XEvents ger en bredare bild för batch/ETL‑källor som inte passerar proxyn.
- Regler (exempel):
```json
[
  {"id":"bss-phone-autocorrect","target":"column","selector":"dbo.Customers.Phone","action":"autocorrect","reason":"Normalize E.164","confidence":0.9},
  {"id":"bss-email-required","target":"column","selector":"dbo.Customers.Email","action":"block","reason":"E‑post krävs vid onboarding","confidence":1.0},
  {"id":"bss-no-test-subs","target":"pattern","selector":"INSERT INTO dbo.Subscriptions","action":"block","reason":"Stoppa testabonnemang i prod","confidence":0.9}
]
```
- LLM‑insikter (exempel):
  - ”17% av nya kunder saknar e‑post i kanal ’retail‑tablet’. Lägg enkel UI‑validering.”
  - ”Vanligaste fel: felaktigt format på telefon. Autocorrect normaliserar 62% till E.164.”
  - ”Föreslår regel: blockera INSERT på Subscriptions med dummy‑domäner (@test.local).”

### Bokningssystem
- Typiska problem:
  - Dubbelbokningar, ogiltiga datumintervall, kundfält saknas, otydliga avbokningsorsaker.
- Regler (exempel):
```json
[
  {"id":"booking-no-overlap","target":"pattern","selector":"INSERT INTO dbo.Bookings","action":"block","reason":"Överlappande tider måste hanteras i app‑logik","confidence":0.8},
  {"id":"booking-email-format","target":"column","selector":"dbo.Bookings.Email","action":"autocorrect","reason":"Korrigera vanliga typos","confidence":0.7}
]
```
- LLM‑insikter (exempel):
  - ”5% av bokningarna har avvikande sluttid < starttid i kanal ’kiosk’ – åtgärda UI.”
  - ”Föreslår autosvar: bekräfta avbokningar med standardtext, minskar manuella ärenden.”
  - ”Skapa enkel business‑regel: blockera re‑book inom 2 min (mis‑tap).”

### ServiceNow (ITSM/ärenden)
- Typiska problem:
  - Saknade fält i incidenter (CI, påverkan, kontakt), felaktig kategorisering, låg datakvalitet i manuellt skapade ärenden.
  - Svårt att se var flöden läcker (t.ex. ärenden som studsar mellan grupper).
- Regler (exempel):
```json
[
  {"id":"sn-caller-required","target":"column","selector":"dbo.Incidents.Caller","action":"block","reason":"Caller måste anges","confidence":1.0},
  {"id":"sn-category-autocorrect","target":"column","selector":"dbo.Incidents.Category","action":"autocorrect","reason":"Normalisera fria texter till kända kategorier","confidence":0.8}
]
```
- LLM‑insikter (exempel):
  - ”Incidenttyp ’VPN’ saknar CI i 28% – uppdatera portalformulär med kravfält.”
  - ”Kö ’ServiceDesk L1’ loopar ofta till ’Network’ och tillbaka. Skapa regel: auto‑kategorisera när beskrivning matchar ’AnyConnect’.”
  - ”Prognos: SLA‑risk ökar vecka 42 p.g.a. ökad inflödestakt i kanal e‑post.”

### CRM
- Typiska problem:
  - Dubletter, ofullständiga leads, felaktiga domäner, GDPR‑signaler saknas (samtycke), orealistiska värden i pipeline.
- Regler (exempel):
```json
[
  {"id":"crm-email-normalize","target":"column","selector":"dbo.Leads.Email","action":"autocorrect","reason":"Korrigera vanliga stavfel i e‑postdomäner","confidence":0.7},
  {"id":"crm-consent-required","target":"column","selector":"dbo.Leads.Consent","action":"block","reason":"Samtycke krävs för outreach","confidence":1.0}
]
```
- LLM‑insikter (exempel):
  - ”10% leads saknar landkod – föreslår autofyll baserat på telefonprefix.”
  - ”Föreslår sanering: 420 dubletter i SME‑segmentet (match på e‑post+orgnr).”
  - ”Skapa pipeline‑regel: blockera sannolikhet > 0.9 om ’deal size’ < 1 000 (datakvalitetslukt).”

### Så här kör du end‑to‑end i dev
1) Starta stacken: `docker compose -f compose.yml -f compose.ci.yml up -d --build` (proxy + SQL + Ollama).
2) Lägg till en enkel regel via API:
```bash
curl -s -X POST http://localhost:8080/rules \
  -H 'Content-Type: application/json' \
  -d '{"id":"phone-autocorrect","target":"column","selector":"Phone","action":"autocorrect","reason":"Normalize SE phone","confidence":0.9}'
```
3) Skapa en minimal demo‑databas (exempel i `docs/howto-integration.md`).
4) Kör några queries via proxyn (port 61433), öppna `http://localhost:8080/metrics.html` och `http://localhost:8080/dryrun.html`.
5) Generera rapporter: `python scripts/generate_daily_report.py` och `python scripts/llm_summarize_profiles.py`.

Tips för produktion:
- Börja i ”log” (dry‑run). Bygg förtroende, mät effekter i `/metrics`, justera regler.
- När ni är nöjda: sätt `ENFORCEMENT_MODE=enforce` för att börja blockera/korregera i begränsad scope (t.ex. bara vissa tabeller/kolumner).
- Publicera insikter: sätt `FEEDBACK_WEBHOOK` för att skicka rapporter till Slack/Jira/ServiceNow (via mellanservice/connector).
