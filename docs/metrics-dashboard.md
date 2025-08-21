# Metrics Dashboard (Prometheus + Grafana)

This repo ships a ready-to-run monitoring profile for a quick overview of key metrics.

## What’s Included
- Prometheus scrape of the proxy at `/metrics/prom`.
- Grafana with a preloaded dashboard showing counters, bytes, and latency quantiles.

## Start Monitoring
```bash
# Start the core stack first
make integration-up
# Then start monitoring profile
make metrics-up
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## Files
- `compose.metrics.yml`: Prometheus and Grafana services.
- `monitoring/prometheus.yml`: scrape config pointing to `proxy:8080/metrics/prom`.
- `monitoring/grafana-provisioning`: datasource + dashboards provisioning.
- `monitoring/dashboards/sqlumai_dashboard.json`: example dashboard.

## Stop Monitoring
```bash
make metrics-down
```
