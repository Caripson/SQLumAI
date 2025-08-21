import importlib
import os


def test_metrics_store_inc(tmp_path, monkeypatch):
    monkeypatch.setenv('METRICS_PATH', str(tmp_path / 'metrics.json'))
    ms = importlib.import_module('src.metrics.store')
    importlib.reload(ms)
    ms.inc('allowed', 2)
    ms.inc_rule_action('rX', 'block', 1)
    data = ms.get_all()
    assert data.get('allowed') == 2
    assert data.get('rule:rX:block') == 1
