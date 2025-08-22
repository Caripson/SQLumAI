# SQLumAI Documentation

Welcome to SQLumAI — an AI‑powered, non‑blocking proxy for Microsoft SQL Server. Use this index to navigate all docs.

## Overview
- [Architecture](architecture.md): overall system components and data flow.
- [MVPs](mvp.md): capabilities across MVP 1–4 and configuration overview.

## Enforcement & Policy
- [Enforcement Guide](ENFORCEMENT.md): dry‑run vs enforce, rules model, thresholds, env gating.
- [QA Checklist](qa-checklist.md): release readiness and manual verification steps.
- [Test Strategy](test-strategy.md): coverage goals, patterns, and CI notes.

## How‑To Guides
- [Reports](howto-reports.md): generate daily and dry‑run reports; where artifacts are written.
- [Integration](howto-integration.md): running locally and via Docker, external data sources.
- [Examples](examples.md): small examples of inputs/outputs and typical flows.

## Metrics & Monitoring
- [Metrics Dashboard](metrics-dashboard.md): Prometheus endpoint and Grafana setup.
- [Dry‑Run Chart](dryrun-chart.md): how dry‑run summaries are visualized.

## LLM & Insights
- [LLM Providers](llm-providers.md): local Ollama and OpenAI‑compatible endpoints; environment variables.
- [Insights](insights.md): how decisions and profiles become actionable insights.

## Data & Internals
- [Dry‑Run JSON](dryrun-json.md): on‑disk JSONL formats for decisions and examples.
- [RPC Builder](rpc-builder.md): parameter encoding for SQL Server RPC calls.

## Operations
- [High Availability](ha.md): proxy topology and failover tips.
- [Release Process](release.md): versioning and publish steps.
- [Release Notes](RELEASE_NOTES.md): notable changes by version.

## Performance
- [Benchmarks](benchmarks.md): parser and RPC encoding microbenchmarks and methodology.

Tip: For quick commands, Makefile targets are documented in the repository README (setup, dev, test, fmt, lint, clean).
