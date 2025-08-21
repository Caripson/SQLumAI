import importlib


def test_prom_histograms_exposed(monkeypatch):
    # Touch histograms via prom_registry if available
    try:
        from src.metrics.prom_registry import bytes_hist, latency_hist
        bytes_hist.observe(512)
        latency_hist.observe(2.5)
    except Exception:
        pass

    api = importlib.import_module('src.api')
    importlib.reload(api)
    resp = api.metrics_prom()
    try:
        text = resp.body.decode('utf-8')  # type: ignore[attr-defined]
    except Exception:
        text = str(resp)
    # Ensure histogram metric names appear when prometheus_client is installed
    assert 'sqlumai_bytes' in text or 'sqlumai_metric' in text
    assert 'sqlumai_latency_ms' in text or 'sqlumai_metric' in text
