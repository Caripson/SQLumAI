#!/usr/bin/env python3
"""
Replay dry-run simulation from an events JSONL file.
Each line is a JSON object with optional keys: sql_text, table, column, value.
Loads rules from RULES_PATH (or config/rules.json) and reports counts by action and rule.
Writes a markdown summary under reports/simulate-YYYY-MM-DD_HHMMSS.md.
"""
import argparse
import json
import datetime as dt
from pathlib import Path
from collections import defaultdict, Counter
from src.policy.engine import PolicyEngine, Event, Rule
from src.policy.loader import load_rules
from src.metrics import store as metrics_store


def simulate(input_path: Path, rules_path: str | None = None) -> dict:
    rules = load_rules(rules_path)
    pe = PolicyEngine(rules)
    actions_total = Counter()
    per_rule = defaultdict(lambda: Counter())
    samples = defaultdict(list)

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            ev = Event(
                database=e.get("database"),
                user=e.get("user"),
                sql_text=e.get("sql_text"),
                table=e.get("table"),
                column=e.get("column"),
                value=e.get("value"),
            )
            dec = pe.decide(ev)
            action = (dec.action or "").lower()
            actions_total[action] += 1
            rid = dec.rule_id or "(no_rule)"
            per_rule[rid][action] += 1
            if len(samples[rid]) < 3:
                samples[rid].append(e.get("sql_text") or e.get("value") or "")
            # Increment simple metrics counters for visibility
            try:
                metrics_store.inc(action or "decided", 1)
                if dec.rule_id:
                    metrics_store.inc_rule_action(dec.rule_id, action or "decided", 1)
            except Exception:
                pass

    return {"actions": dict(actions_total), "per_rule": {k: dict(v) for k, v in per_rule.items()}, "samples": samples}


def write_report(results: dict) -> Path:
    outdir = Path("reports")
    outdir.mkdir(exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    out = outdir / f"simulate-{ts}.md"
    lines = [f"# Dry‑Run Simulation – {ts}", "", "## Totals by Action"]
    for k, v in sorted(results.get("actions", {}).items(), key=lambda kv: kv[0]):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## By Rule")
    for rid, acts in results.get("per_rule", {}).items():
        parts = ", ".join(f"{k}:{v}" for k, v in sorted(acts.items()))
        lines.append(f"- {rid}: {parts}")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to events JSONL")
    ap.add_argument("--rules", help="Rules JSON path (optional)")
    args = ap.parse_args()
    p = Path(args.input)
    if not p.exists():
        raise SystemExit(f"Input not found: {p}")
    results = simulate(p, args.rules)
    out = write_report(results)
    print(f"Wrote simulation report to {out}")


if __name__ == "__main__":
    main()
