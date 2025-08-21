#!/usr/bin/env python3
"""
Generate LLM-backed insights from decisions.jsonl and field_profiles.json.
Outputs reports/insights-YYYY-MM-DD.md. Falls back to heuristic scoring when LLM is unavailable.
"""
import os
import json
import datetime as dt
from pathlib import Path

DECISIONS = Path("data/metrics/decisions.jsonl")
PROFILES = Path("data/aggregations/field_profiles.json")
REPORTS = Path("reports")


def load_decisions_for_date(date_iso: str):
    out = []
    if not DECISIONS.exists():
        return out
    with DECISIONS.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                if d.get("ts", "").startswith(date_iso):
                    out.append(d)
            except Exception:
                continue
    return out


def try_llm(prompt: str) -> str | None:
    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    model = os.getenv("LLM_MODEL", "llama3.2")
    try:
        import httpx
    except Exception:
        return None
    if provider == "ollama":
        endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
        try:
            r = httpx.post(f"{endpoint}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=30)
            r.raise_for_status()
            return r.json().get("response")
        except Exception:
            return None
    endpoint = os.getenv("LLM_ENDPOINT")
    if not endpoint:
        return None
    try:
        headers = {}
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        r = httpx.post(endpoint, json=payload, headers=headers or None, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("choices"):
            return data["choices"][0]["message"]["content"]
        return None
    except Exception:
        return None


def main():
    date = dt.datetime.utcnow().date().isoformat()
    decisions = load_decisions_for_date(date)
    profiles = {}
    if PROFILES.exists():
        try:
            profiles = json.loads(PROFILES.read_text())
        except Exception:
            profiles = {}

    # Prepare compact context for the LLM
    by_rule = {}
    for d in decisions:
        rid = d.get("rule_id") or "(no_rule)"
        by_rule.setdefault(rid, {"block": 0, "autocorrect": 0, "rpc_autocorrect_inplace": 0}).update()
        act = (d.get("action") or "").lower()
        if act in by_rule[rid]:
            by_rule[rid][act] += 1
    top_profiles = list(profiles.items())[:30]

    prompt_lines = [
        "You are a data quality lead. Using summaries below, produce 5-8 actionable insights with severity, impacted fields, and next steps.",
        "Context:",
        f"Decisions by rule (today {date}):",
    ]
    for rid, counts in by_rule.items():
        prompt_lines.append(f"- {rid}: {counts}")
    prompt_lines.append("Top profiles:")
    for k, v in top_profiles:
        prompt_lines.append(f"- {k}: count={v.get('count',0)} nulls={v.get('nulls',0)} sugg={sum((v.get('suggestions') or {}).values())}")
    prompt = "\n".join(prompt_lines)

    out = try_llm(prompt)
    if not out:
        # Heuristic fallback
        lines = [f"# Insights – {date}", "", "- Increase validation on fields with repeated autocorrect events.", "- Address top missingness columns via UI hints.", "- Align phone/country formats across services."]
        out = "\n".join(lines)
    else:
        out = f"# Insights – {date}\n\n" + out

    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"insights-{date}.md"
    path.write_text(out, encoding="utf-8")
    print(f"Wrote insights to {path}")


if __name__ == "__main__":
    main()

