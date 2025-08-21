# LLM Providers & Configuration

SQLumAI can summarize profiles via a local or remote LLM.

## Environment variables
- `LLM_PROVIDER`: `ollama` or `openai` (generic OpenAI-compatible). Default: none (disabled)
- `LLM_MODEL`: model name (e.g., `llama3.2`, `gpt-4o-mini`). Default: `llama3.2`
- `LLM_ENDPOINT`:
  - Ollama: `http://ollama:11434` (in Compose) or `http://localhost:11434`
  - OpenAI-compatible: e.g., `https://api.openai.com/v1/chat/completions`
- `LLM_SEND_EXTERNAL`: `true|false` — choose carefully if sending data off-host (default false in `.env.example`)

## Ollama (local, default in Compose)
- Compose launches an `ollama` service and sets env for the proxy.
- First pull can take time; warm up the model:

```bash
make integration-up
make llm-pull MODEL=llama3.2
```

- Generate a summary:

```bash
docker exec proxy python scripts/llm_summarize_profiles.py
```

## OpenAI-compatible endpoint
- Set the following in `.env` or environment:

```bash
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o-mini
export LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
export OPENAI_API_KEY=...   # if your endpoint requires Authorization header
```

- Adjust `scripts/llm_summarize_profiles.py` if your endpoint needs auth headers.

## Safety & privacy
- Keep `LLM_SEND_EXTERNAL=false` by default.
- Use Ollama for on-host inference to avoid sending data externally.
