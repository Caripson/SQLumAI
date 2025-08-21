# Test Strategy

## Coverage Policy
- Target: 92% locally, CI gate at 90%.
- Exclusions: network-heavy and process entrypoints omitted via `.coveragerc`:
  - `src/proxy/*`, `src/main.py`, and the thin file loader.
- Philosophy: cover logic-heavy modules (API handlers, metrics, policy engine, parsing, LLM utilities).

## Running Tests Efficiently
- Quick run: `make test` (or `python3 -m pytest -q`).
- Coverage 90%: `make test-90` (or `python3 -m pytest --cov=src --cov-report=term-missing --cov-fail-under=90`).
- Speed up locally:
  - Use `-k` to select subsets, e.g. `-k 'not proxy'` to skip socket tests.
  - Re-run failures only: `-k 'last_failed or <pattern>'`.

## Integration and E2E
- Start stack: `make integration-up` (proxy+SQL Server+API), optional: `make llm-pull`.
- LLM smoke: `docker compose exec -T proxy python scripts/llm_summarize_profiles.py`.
- Dashboards: `make metrics-up` (Prometheus at 9090, Grafana at 3000).

## Notes on Environments
- CI uses Docker Compose and jq assertions; metrics counters are bumped as fallback to avoid flakiness.
- Sandbox environments may restrict sockets; prefer function-level tests (calling API handlers directly) instead of TestClient.
