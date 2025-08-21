import os
import importlib
import json
from pathlib import Path


def test_llm_insights_fallback(tmp_path, monkeypatch):
    # Prepare minimal decisions and profiles
    (tmp_path / 'data/metrics').mkdir(parents=True)
    (tmp_path / 'data/aggregations').mkdir(parents=True)
    today = '2025-01-01'
    (tmp_path / 'data/metrics/decisions.jsonl').write_text(json.dumps({"ts": today + 'T00:00:00Z', "action": "autocorrect", "rule_id": "r1"}) + "\n", encoding='utf-8')
    (tmp_path / 'data/aggregations/field_profiles.json').write_text(json.dumps({"dbo.T.Col": {"count": 1, "nulls": 0, "suggestions": {"phone": 1}}}), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    # Force no LLM
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    scripts = importlib.import_module('scripts.llm_insights')
    importlib.reload(scripts)
    scripts.main()
    reports = list((tmp_path / 'reports').glob('insights-*.md'))
    assert reports, 'insights report not generated'
