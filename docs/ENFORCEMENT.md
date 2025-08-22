# Enforcement Overview

This document explains how SQLumAI evolves from passive monitoring to selective, auditable enforcement.

## Flow
- Collect: XEvents capture query text, parameters, timings, and outcomes.
- Analyze: Aggregations build field profiles; LLM proposes fixes and policy candidates.
- Approve: Data team reviews proposals, promotes them to rules via the Rules API.
- Enforce: The proxy applies rules inline without blocking unrelated traffic.

## Modes
- allow: Pass data unchanged (default/fail‑open).
- autocorrect: Apply safe, reversible transforms (e.g., trim, phone country code).
- block: Reject operations that violate hard constraints (e.g., forbidden values).

## Inline Enforcement
- TLS termination (optional): Enable `TLS_TERMINATION=true` so the proxy can read TDS packets.
- TDS parsing: Decode packet headers now; extend to Batch/RPC payloads to map values to columns.
- Policy engine: For each candidate value, evaluate rules in order; emit decision (allow/autocorrect/block) + reason + confidence.

### SQL Batch (0x01)
- Reassemble full batch, decode as UTF‑16LE; apply pattern/table rules.
- Column‑level mapping for simple INSERT/UPDATE via a best‑effort regex parser; safe SQL text rewrite when `ENFORCEMENT_MODE=enforce`.
- Multirow INSERT support: rewrite `(…), (…)` groups when the number of columns matches the number of values.

### RPC (0x03)
- Reassemble RPC payload; heuristic extraction of NVARCHAR parameters.
- In‑place autocorrect (utf‑16le) when the new value is not longer than the original (shorter padded with spaces) when `RPC_AUTOCORRECT_INPLACE=true`.
- Block RPC on rule match when `ENFORCEMENT_MODE=enforce`.

## Traceability & Safety
- Logging: Every correction/block records rule id, reason, confidence, original and resulting value.
- Fail‑open by default: If parsing or policy evaluation fails, pass traffic unchanged and log context.
- Rollback: Disabling a rule (via API or config) immediately stops enforcement for that selector.

## Rule Lifecycle
1) Proposal: LLM suggests rules (kind, selector, action, confidence).
2) Review: Humans validate impact; stage as `autocorrect` first where possible.
3) Promote: Switch to `block` for critical violations once false positive rate is acceptable.
4) Monitor: Track metrics (auto‑corrections, blocks, false positives) to tune thresholds.

## Feature flags / Env gating
- Per‑rule controls: `enabled: true/false`, `apply_in_envs: ["dev","staging","prod"]` to limit where rules apply.
- Global toggles: `ENABLE_TDS_PARSER`, `ENABLE_SQL_TEXT_SNIFF`, `ENFORCEMENT_MODE`, `RPC_AUTOCORRECT_INPLACE`, `TIME_BUDGET_MS`, `MAX_REWRITE_BYTES`.

## TDS Parser Scope and Risk
- SQL Server’s TDS protocol is complex. SQLumAI’s parsing is intentionally minimal and best‑effort to keep the hot path safe.
- Supported today: UTF‑16LE batch text for simple INSERT/UPDATE matching and heuristic NVARCHAR RPC parameter extraction.
- Not guaranteed: unusual datatypes, vendor‑specific RPCs, newer protocol nuances. On parse failure, the proxy fails open and logs context.
- Roadmap: consider contributing to or integrating a robust external TDS library. Contributions welcome.

## Performance
- Keep parsing minimal (batch/statement only); avoid heavy transforms on the hot path.
- Batch reports and webhooks out‑of‑band via the scheduler.
