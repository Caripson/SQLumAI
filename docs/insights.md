# LLM Insights

SQLumAI can synthesize daily insights from decisions (autocorrects/blocks) and field profiles.

- Script: `scripts/llm_insights.py`
- Output: `reports/insights-YYYY-MM-DD.md`
- Scheduler: runs automatically when `ENABLE_SCHEDULER=true`.

Environment
- `LLM_PROVIDER`: `ollama` (default in Compose) or `openai`.
- `LLM_MODEL`: e.g., `llama3.2` (Ollama) or `gpt-4o-mini` (OpenAI-compatible).
- `LLM_ENDPOINT`: Ollama `http://ollama:11434` or your chat completions endpoint.
- `OPENAI_API_KEY`: used when `LLM_PROVIDER=openai`.

Heuristic fallback
- If an LLM is not reachable, a short heuristic set of insights is generated.

Tips
- Ensure `data/aggregations/field_profiles.json` and `data/metrics/decisions.jsonl` exist to get richer insights.
