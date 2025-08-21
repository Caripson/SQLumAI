#!/usr/bin/env python3
"""
Summarize aggregated profiles via a local LLM when available.
Reads data/aggregations/field_profiles.json and writes reports/llm-summary-YYYY-MM-DD.md.
If LLM_ENDPOINT is not set or not reachable, falls back to heuristic summary.
"""
import os
import json
import datetime as dt
from pathlib import Path

PROFILES = Path("data/aggregations/field_profiles.json")
REPORTS_DIR = Path("reports")


def try_llm(prompt: str) -> str | None:
    provider = (os.getenv("LLM_PROVIDER") or "").lower()
    model = os.getenv("LLM_MODEL", "llama3.2")
    try:
        import httpx
    except Exception:
        return None

    # Ollama provider
    if provider == "ollama":
        endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
        try:
            r = httpx.post(f"{endpoint}/api/generate", json={"model": model, "prompt": prompt, "stream": False}, timeout=30)
            r.raise_for_status()
            data = r.json()
            return data.get("response")
        except Exception:
            return None

    # Generic OpenAI-compatible
    endpoint = os.getenv("LLM_ENDPOINT")
    if not endpoint:
        return None
    try:
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
        headers = {}
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        r = httpx.post(endpoint, json=payload, headers=headers or None, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            if "content" in data:
                return data["content"]
        return None
    except Exception:
        return None


def main():
    if not PROFILES.exists():
        print("No profiles found; skipping LLM summary.")
        return
    profiles = json.loads(PROFILES.read_text())
    sample = []
    for k, v in list(profiles.items())[:50]:
        sugg = v.get("suggestions", {})
        sample.append(f"- {k}: count={v.get('count',0)} nulls={v.get('nulls',0)} suggestions={sum(sugg.values())}")
    prompt = (
        "You are a data quality assistant. Summarize the most significant issues and next best actions "
        "from the following per-field profiles. Group by themes (missingness, format issues, drift candidates) and propose 3-5 concrete actions.\n\n"
        + "\n".join(sample)
    )

    # Optional template
    tpl = os.getenv("LLM_TEMPLATE", "profiles").lower()
    tpl_map = {
        "profiles": Path("templates/llm/profiles.txt"),
        "drift": Path("templates/llm/drift.txt"),
        "errors": Path("templates/llm/errors.txt"),
    }
    if tpl in tpl_map and tpl_map[tpl].exists():
        intro = tpl_map[tpl].read_text(encoding="utf-8")
        prompt = intro + "\n\n" + prompt

    out = try_llm(prompt)
    if not out:
        # Heuristic summary
        top_missing = sorted(profiles.items(), key=lambda kv: kv[1].get("nulls", 0), reverse=True)[:5]
        top_sugg = sorted(((k, sum(v.get("suggestions", {}).values())) for k, v in profiles.items()), key=lambda kv: kv[1], reverse=True)[:5]
        lines = [
            "LLM not available; heuristic summary:",
            "", "Top Missingness:",
        ]
        for k, v in top_missing:
            lines.append(f"- {k}: nulls={v.get('nulls',0)} count={v.get('count',0)}")
        lines.append("")
        lines.append("Format Issues:")
        for k, n in top_sugg:
            lines.append(f"- {k}: {n} suggestions")
        out = "\n".join(lines)

    REPORTS_DIR.mkdir(exist_ok=True)
    date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"llm-summary-{date}.md"
    path.write_text(out, encoding="utf-8")
    print(f"Wrote LLM summary to {path}")


if __name__ == "__main__":
    main()
