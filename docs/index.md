# SQLumAI Documentation

Welcome to SQLumAI — an AI‑powered, non‑blocking proxy for Microsoft SQL Server. Use this index to navigate all docs.

## Overview
- Architecture: overall system components and data flow. See architecture.md
- MVPs: capabilities across MVP 1–4 and configuration overview. See mvp.md

## Enforcement & Policy
- Enforcement Guide: dry‑run vs enforce, rules model, thresholds, env gating. See ENFORCEMENT.md
- QA Checklist: release readiness and manual verification steps. See qa-checklist.md
- Test Strategy: coverage goals, patterns, and CI notes. See test-strategy.md

## How‑To Guides
- Reports: generate daily and dry‑run reports; where artifacts are written. See howto-reports.md
- Integration: running locally and via Docker, external data sources. See howto-integration.md
- Examples: small examples of inputs/outputs and typical flows. See examples.md

## Metrics & Monitoring
- Metrics Dashboard: Prometheus endpoint and Grafana setup. See metrics-dashboard.md
- Dry‑Run Chart: how dry‑run summaries are visualized. See dryrun-chart.md

## LLM & Insights
- LLM Providers: local Ollama and OpenAI‑compatible endpoints; environment variables. See llm-providers.md
- Insights: how decisions and profiles become actionable insights. See insights.md

## Data & Internals
- Dry‑Run JSON: on‑disk JSONL formats for decisions and examples. See dryrun-json.md
- RPC Builder: parameter encoding for SQL Server RPC calls. See rpc-builder.md

## Operations
- High Availability: proxy topology and failover tips. See ha.md
- Release Process: versioning and publish steps. See release.md
- Release Notes: notable changes by version. See RELEASE_NOTES.md

## Performance
- Benchmarks: parser and RPC encoding microbenchmarks and methodology. See benchmarks.md

Tip: For quick commands, Makefile targets are documented in the repository README (setup, dev, test, fmt, lint, clean).
