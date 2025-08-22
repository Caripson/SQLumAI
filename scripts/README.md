# Scripts Overview

Brief descriptions of helper scripts. Most scripts are optional and intended for manual or scheduled runs.

- aggregate_profiles.py: Aggregate XEvent JSONL into `data/aggregations/field_profiles.json` and simple SELECT stats.
- bench_proxy.py: Micro-benchmark for SQL parsing and RPC payload building hot paths.
- generate_daily_report.py: Build daily data-quality report from `field_profiles.json` into `reports/report-YYYY-MM-DD.md`.
- generate_dryrun_report.py: Summarize `data/metrics/decisions.jsonl` into `reports/dryrun-YYYY-MM-DD.md`.
- llm_insights.py: Produce insights from decisions + profiles; writes `reports/insights-YYYY-MM-DD.md` (LLM optional, with heuristic fallback).
- llm_summarize_profiles.py: Summarize profiles via local/remote LLM; writes `reports/llm-summary-YYYY-MM-DD.md` (heuristic fallback if no LLM).
- publish_feedback.py: Post the latest `reports/report-*.md` to a webhook (`FEEDBACK_WEBHOOK`) or write payload to `outbox/`.
- read_xel_files.py: Read server-side `.xel` files via T-SQL `fn_xe_file_target_read_file`; emits normalized JSON lines.
- read_xevents.py: Read ring buffer for `sqlumai_capture`; writes raw JSONL and updates `field_profiles.json`.
- replay_dryrun.py: Simulate policy decisions from an events JSONL; writes `reports/simulate-YYYY-MM-DD_HHMMSS.md`.
- setup_xevents.py: Render minimal SQL to create the `sqlumai_capture` XEvents session (ring buffer or file target).
- validate_rules.py: Validate `config/rules.json` against API schema; exits non-zero on errors.

SQL helpers
- create_xevents.sql: Ready-made ring buffer XEvents setup.
- create_xevents_file.sql: XEvents setup using file target.
- drop_xevents.sql: Tear down existing XEvents sessions.

Environment hints
- MSSQL_DSN/SQL_HOST…: Required by `read_xevents.py` and `read_xel_files.py` for ODBC access.
- LLM_PROVIDER/LLM_ENDPOINT/OPENAI_API_KEY: Optional for `llm_*` scripts; they fall back to heuristics when unavailable.

Usage
- Python: `python scripts/<name>.py [args]`
- Make targets: see `make help` for `report-dryrun`, `validate-rules`, and cleaning helpers (`clean*`).
