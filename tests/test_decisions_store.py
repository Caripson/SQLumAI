import importlib
import os


def test_decisions_append_and_tail(tmp_path, monkeypatch):
    monkeypatch.setenv('DECISIONS_PATH', str(tmp_path / 'decisions.jsonl'))
    mod = importlib.import_module('src.metrics.decisions')
    importlib.reload(mod)
    mod.append({'action': 'allow'})
    tail = mod.tail(10)
    assert tail and tail[-1]['action'] == 'allow'
