import os
import importlib
import pytest


fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    return api.app


def test_rules_ui_and_test_endpoint(tmp_path, monkeypatch):
    app = setup_app(tmp_path, monkeypatch)
    c = TestClient(app)
    # UI
    r = c.get("/rules/ui")
    assert r.status_code == 200 and "Rules UI" in r.text
    # Test endpoint default allow
    r2 = c.post("/rules/test", json={"table": "dbo.T", "column": "dbo.T.Email", "value": ""})
    assert r2.status_code == 200 and r2.json().get("action") in ("allow", "block", "autocorrect")


def test_xevents_setup_and_suggest(tmp_path, monkeypatch):
    app = setup_app(tmp_path, monkeypatch)
    c = TestClient(app)
    r = c.post("/xevents/setup", params={"mode": "ring"})
    assert r.status_code == 200 and "CREATE EVENT SESSION" in r.json().get("sql", "")
    s = c.post("/rules/suggest", json={"text": "Email måste vara obligatorisk"})
    assert s.status_code == 200 and s.json().get("target") in ("column", "pattern")

