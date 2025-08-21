# How-To: Reports

## Daily Data Quality Report
 - Collect events: `python scripts/read_xevents.py` or `python scripts/read_xel_files.py`.
 - Aggregate: `python scripts/aggregate_profiles.py`.
 - Generate: `python scripts/generate_daily_report.py` → `reports/report-YYYY-MM-DD.md`.

### SELECT Analysis
Från och med MVP 4 innehåller rapporten en sektion “SELECT Analysis” med:
- `select_star` per tabell (antal `SELECT *`).
- Topplista över mest valda kolumner.

Detta kommer från `scripts/aggregate_profiles.py` som nu skriver både `profiles` och `selects` i `data/aggregations/field_profiles.json`.

### Drift (Null-ratio)
En enkel null‑driftsektion visas om en tidigare snapshot finns på `data/aggregations/field_profiles.prev.json`.
Skapa en kopia av gårdagens profiler innan du kör ny aggregation:
```bash
cp data/aggregations/field_profiles.json data/aggregations/field_profiles.prev.json
python scripts/aggregate_profiles.py
python scripts/generate_daily_report.py
```
Rapporten listar fält där förändringen i null‑kvot överstiger 0.10.

## Dry-Run Enforcement Summary
- Ensure decisions are being logged (default when `ENFORCEMENT_MODE=log`).
- Generate: `python scripts/generate_dryrun_report.py` → `reports/dryrun-YYYY-MM-DD.md`.
- Scheduler also runs this if enabled (`ENABLE_SCHEDULER=true`).
