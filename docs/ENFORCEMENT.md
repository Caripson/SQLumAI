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
- Reassembly of full batch, decode as UTF‑16LE; apply pattern/table rules.
- Column‑level mapping for simple INSERT/UPDATE via regex parser; safe rewrite of SQL text when `ENFORCEMENT_MODE=enforce`.
- Multirow INSERT stöd: omskrivning av `(…), (…)` block när kolumn‑värde‑antal matchar.

### RPC (0x03)
- Reassembly av RPC payload; heuristisk extraktion av NVARCHAR‑parametrar.
- In‑place autocorrect (utf‑16le) när nya värdet inte är längre än det gamla (kortare pad: spaces) när `RPC_AUTOCORRECT_INPLACE=true`.
- Blockering av RPC vid regelmatchning när `ENFORCEMENT_MODE=enforce`.

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
- Per‑regel: `enabled: true/false`, `apply_in_envs: ["dev","staging","prod"]` för att styra var regler gäller.
- Globala toggles: `ENABLE_TDS_PARSER`, `ENABLE_SQL_TEXT_SNIFF`, `ENFORCEMENT_MODE`, `RPC_AUTOCORRECT_INPLACE`, `TIME_BUDGET_MS`, `MAX_REWRITE_BYTES`.

## Performance
- Keep parsing minimal (batch/statement only); avoid heavy transforms on the hot path.
- Batch reports and webhooks out‑of‑band via the scheduler.
