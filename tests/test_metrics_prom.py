import importlib


def test_prom_exposition(monkeypatch):
    # Ensure counters have a value
    from src.metrics import store as ms
    ms.inc('allowed', 2)
    api = importlib.import_module('src.api')
    importlib.reload(api)
    resp = api.metrics_prom()
    # metrics_prom can return a Response (prometheus) or text fallback
    try:
        # FastAPI Response
        body = resp.body.decode('utf-8')  # type: ignore[attr-defined]
    except Exception:
        body = str(resp)
    assert 'sqlumai' in body
