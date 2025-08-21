import importlib
import sys


def test_metrics_prom_fallback(monkeypatch):
    # Force fallback by injecting a dummy prometheus_client without generate_latest
    class Dummy:
        pass
    sys.modules['prometheus_client'] = Dummy()  # type: ignore
    api = importlib.import_module('src.api')
    importlib.reload(api)
    resp = api.metrics_prom()
    body = resp.body.decode('utf-8') if hasattr(resp, 'body') else str(resp)
    assert '# TYPE sqlumai_metric counter' in body
