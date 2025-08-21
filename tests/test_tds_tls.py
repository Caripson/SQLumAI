import asyncio


def test_run_tls_terminating_proxy_bad_cert(monkeypatch):
    # Force missing cert/key to trigger error path
    monkeypatch.setenv('TLS_CERT_PATH', '/no/such/cert.pem')
    monkeypatch.setenv('TLS_KEY_PATH', '/no/such/key.pem')
    from src.proxy.tds_tls import run_tls_terminating_proxy
    def _go():
        async def run():
            try:
                await run_tls_terminating_proxy('127.0.0.1', 0, '127.0.0.1', 0, asyncio.Event())
            except Exception:
                return True
            return False
        return asyncio.run(run())
    assert _go() is True
