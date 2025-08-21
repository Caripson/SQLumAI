import importlib
import json
import pytest


fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


def setup_app(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    monkeypatch.setenv("PROPOSED_RULES_PATH", str(tmp_path / "rules_proposed.json"))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    return api.app


def test_gitops_rules_diff_and_promote(tmp_path, monkeypatch):
    app = setup_app(tmp_path, monkeypatch)
    c = TestClient(app)
    # Proposed add
    r = c.post("/rules/proposed", json={"id":"p1","target":"table","selector":"dbo.T","action":"allow"})
    assert r.status_code == 200
    # Diff should show one added
    d = c.get("/rules/diff").json()
    assert len(d.get("added", [])) == 1
    # Promote
    p = c.post("/rules/promote").json()
    assert p.get("promoted") == 1
    # Current rules should include p1
    cur = c.get("/rules").json()
    assert any(x.get("id") == "p1" for x in cur)

