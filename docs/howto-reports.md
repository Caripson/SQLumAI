# How-To: Reports

## Daily Data Quality Report
- Collect events: `python scripts/read_xevents.py` or `python scripts/read_xel_files.py`.
- Aggregate: `python scripts/aggregate_profiles.py`.
- Generate: `python scripts/generate_daily_report.py` → `reports/report-YYYY-MM-DD.md`.

## Dry-Run Enforcement Summary
- Ensure decisions are being logged (default when `ENFORCEMENT_MODE=log`).
- Generate: `python scripts/generate_dryrun_report.py` → `reports/dryrun-YYYY-MM-DD.md`.
- Scheduler also runs this if enabled (`ENABLE_SCHEDULER=true`).
