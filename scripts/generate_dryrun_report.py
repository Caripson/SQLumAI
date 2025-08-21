#!/usr/bin/env python3
import json
import datetime as dt
from pathlib import Path
from collections import defaultdict, Counter

DECISIONS = Path("data/metrics/decisions.jsonl")
REPORTS_DIR = Path("reports")


def iter_decisions_for_date(date: dt.date):
    if not DECISIONS.exists():
        return []
    target_prefix = date.isoformat()
    with DECISIONS.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                ts = d.get("ts", "")
                if ts.startswith(target_prefix):
                    yield d
            except Exception:
                continue


def main():
    today = dt.datetime.utcnow().date()
    actions_total = Counter()
    per_rule = defaultdict(lambda: Counter())
    samples = defaultdict(list)

    for d in iter_decisions_for_date(today):
        action = str(d.get("action", "")).lower()
        rule_id = d.get("rule_id") or "(no_rule)"
        actions_total[action] += 1
        per_rule[rule_id][action] += 1
        if len(samples[rule_id]) < 3:
            samples[rule_id].append(d.get("sample") or d.get("before") or "")

    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"dryrun-{today.isoformat()}.md"
    lines = [
        f"# Dry‑Run Enforcement Summary – {today.isoformat()}",
        "",
        "## Totals by Action",
    ]
    for k, v in actions_total.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## By Rule")
    for rule, cnts in per_rule.items():
        parts = ", ".join(f"{k}:{v}" for k, v in cnts.most_common())
        lines.append(f"- {rule}: {parts}")
        for s in samples[rule]:
            if s:
                clean = s.replace("\n", " ")
                lines.append(f"  - sample: {clean[:160]}")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote dry‑run report to {out}")


if __name__ == "__main__":
    main()

