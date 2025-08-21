# MVP 1–3 Overview

## MVP 4: Enforcement and DX
- SQL coverage: detectors for MERGE, BULK INSERT, and read‑only SELECT analysis for hotspots (SELECT * counts, column usage).
- Types: RPC builder support for DECIMAL/NUMERIC, DATE/TIME/DATETIME2/DATETIMEOFFSET, UNIQUEIDENTIFIER, VARBINARY.
- Normalizers: decimal, datetime, uuid.
- UI: lightweight Rules UI at `/rules/ui` with a “Test Decision” panel.
- Ops: XEvents setup helper script and secrets provider abstraction.

## MVP 1: Pass‑through and snapshots
- Transparent TCP proxy for TDS; no blocking.
- Capture query text/params via SQL Server Extended Events (ring buffer or event_file).
- Scripts: `scripts/create_xevents.sql`, `scripts/read_xevents.py`, `scripts/read_xel_files.py`.
- Aggregation and daily reports: `scripts/aggregate_profiles.py`, `scripts/generate_daily_report.py`.

## MVP 2: Format fixes and feedback
- Normalizers for dates/phone/postal/email/country/orgnr in `agents/normalizers.py`.
- Suggestions appear in daily report; webhook feedback supported.
- Implicit catalogue via SQL parsing; insights via LLM summary.

## MVP 3: Gatekeeper and adaptive rules
- Rules API + engine, env‑gating, per‑regel thresholds.
- Optional TLS termination + TDS parser for batch/RPC; column‑level autocorrect for simple INSERT/UPDATE; RPC in‑place autocorrect.
- Metrics, audits, dashboards, and insights.

## Key Toggles
- Dry‑run vs enforce: `ENFORCEMENT_MODE=log|enforce`.
- Parsers: `ENABLE_TDS_PARSER=true`, `ENABLE_SQL_TEXT_SNIFF=true`.
- LLM: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_ENDPOINT`, `OPENAI_API_KEY`.
- Scheduler: `ENABLE_SCHEDULER`, `SCHEDULE_INTERVAL_SEC`.

## Helpful Links
- Architecture: `docs/architecture.md`
- Enforcement: `docs/ENFORCEMENT.md`
- Insights: `docs/insights.md`
- LLM Providers: `docs/llm-providers.md`
- How-To (reports/integration): `docs/howto-reports.md`, `docs/howto-integration.md`
