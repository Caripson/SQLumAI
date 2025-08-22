# TDS Parser Support Matrix

This document outlines what the built‑in TDS handling currently supports, what is explicitly out of scope, and the safety posture. The goal is transparency so operators can decide when to enable parsing and enforcement.

## Philosophy
- Keep the hot path safe and fast: minimal, best‑effort parsing only where it adds value.
- Fail open: if parsing or mapping fails, the proxy forwards traffic unchanged and logs context.
- Prefer explicit rules over heavy rewrites; keep autocorrects reversible and auditable.

## Summary Matrix

| Area | Support | Notes |
|------|---------|-------|
| TDS packet headers | Basic | Used for flow control and identifying packet types. |
| SQL Batch (0x01) reassembly | Yes | UTF‑16LE decoding to recover batch text. |
| SQL text analysis | Limited | Best‑effort regex for simple INSERT/UPDATE detection. |
| Column mapping (INSERT) | Limited | Match column list to VALUES tuples when counts align. |
| Multi‑row INSERT | Limited | Rewrites supported only when column/value counts match per tuple. |
| Column mapping (UPDATE) | Limited | Heuristic mapping of SET column=value pairs (simple cases). |
| MERGE/BULK/CTE/complex SQL | No | Not parsed beyond basic pattern checks; no rewrites. |
| RPC (0x03) reassembly | Yes | Reconstruct payload for parameter extraction. |
| RPC parameter types | Partial | Heuristic NVARCHAR extraction; other types not guaranteed. |
| In‑place RPC autocorrect | Optional | When `RPC_AUTOCORRECT_INPLACE=true` and new value is not longer. |
| TLS termination | Optional | Off by default; required to read payloads on the proxy. |

## Supported Scenarios (Examples)
- Detect and optionally rewrite trivial `INSERT INTO dbo.Table (A,B) VALUES ("x","y")` when rules target specific columns.
- Heuristically extract NVARCHAR RPC parameters for rule checks and lightweight autocorrect when safe in place.

## Not Covered / Limitations
- Unusual or newer SQL Server datatypes (e.g., SQL_VARIANT, XML, TVP) are not guaranteed.
- Vendor‑specific RPCs or non‑standard encodings.
- Complex SQL constructs (MERGE, CTEs, nested queries) — analysis is pattern‑level only; no rewrites.

## Safety & Failure Modes
- Fail‑open by default: undecided/failed parsing → forward unchanged and log.
- Bounded rewrites: controlled by `TIME_BUDGET_MS` and `MAX_REWRITE_BYTES`.
- Auditable: all corrections/blocks include rule id, reason, and confidence in logs/metrics.

## Configuration
- Feature toggles: `ENABLE_TDS_PARSER`, `ENABLE_SQL_TEXT_SNIFF`, `ENFORCEMENT_MODE`, `RPC_AUTOCORRECT_INPLACE`, `TIME_BUDGET_MS`, `MAX_REWRITE_BYTES`.
- TLS termination: `TLS_TERMINATION`, `TLS_CERT_PATH`, `TLS_KEY_PATH`.

## Tests & Coverage
- Unit tests for batch/RPC parsing heuristics live under `tests/` (e.g., `test_tds_parser.py`, `test_rpc_parse.py`).
- Integration tests are gated by environment variables and are optional (`ENABLE_INTEGRATION_TESTS`).

## Roadmap: External TDS Library
To reduce protocol risk and broaden support, consider adopting or contributing to a robust TDS implementation. Evaluation criteria:
- Protocol coverage (packets, datatypes, RPC formats, TLS).
- Performance characteristics and memory footprint suitable for a proxy.
- License compatibility (MIT‑friendly) and maintenance activity.
- Extensibility hooks for safely mapping parameters to columns.

If you have experience with suitable libraries or are interested in collaborating, please open an issue or PR.

