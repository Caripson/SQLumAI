# High Availability (HA) Overview

- Run multiple proxy instances behind a load balancer; keep them stateless.
- Centralize rules via the API or Git (mounted `config/rules.json`) and reload on change.
- Prefer sticky connections only when TLS termination occurs at the proxy; otherwise TCP pass‑through is safe.
- Health probes: `/healthz`; readiness may include a quick upstream connect test.
- Metrics scraping: `/metrics/prom` for Prometheus; ship dashboards in `docs/metrics-dashboard.md`.

Notes
- Start with dry‑run in production; gradually enable enforcement by table/column.
- Use `SECRET_PROVIDER=file` with mounted secret files or cloud secret stores via sidecars.

