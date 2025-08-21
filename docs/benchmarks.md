# Benchmarks

This page shows simple, reproducible micro-benchmarks for parser and RPC encoder hot paths.

Run locally:
```bash
python scripts/bench_proxy.py
# Example output:
# parse: 0.012s for 10k; rpc: 0.020s for 5k
```

Guidance
- Run on a quiet machine and repeat 3x; report the median.
- Compare with and without `ENABLE_TDS_PARSER=true` in end-to-end tests for realistic latency.
- For proxy network latency, prefer end-to-end `wrk`/`bombardier`-style tests against a dev SQL Server.

Contributions
- Add a short note (CPU, Python, OS) and paste timing output under a new section.
- Do not check in large datasets or external dependencies.

