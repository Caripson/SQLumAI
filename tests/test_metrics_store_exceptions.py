import importlib
import os


def test_metrics_store_exceptions(tmp_path, monkeypatch):
    # Invalid JSON to trigger _read exception path
    mpath = tmp_path / 'metrics.json'
    mpath.write_text('{invalid', encoding='utf-8')
    monkeypatch.setenv('METRICS_PATH', str(mpath))
    ms = importlib.import_module('src.metrics.store')
    importlib.reload(ms)
    assert ms.get_all() == {}

    # Monkeypatch prom_inc to raise and hit except branches
    ms.prom_inc = lambda *a, **k: (_ for _ in ()).throw(Exception('boom'))
    ms.inc('allowed', 1)
    ms.inc_rule_action('rZ', 'block', 1)
    # get_rule_counters path
    counters = ms.get_rule_counters('rZ')
    assert counters.get('block') == 1
