import os
import importlib
from fastapi.testclient import TestClient


def test_rules_crud(tmp_path, monkeypatch):
    rules_path = tmp_path / "rules.json"
    monkeypatch.setenv("RULES_PATH", str(rules_path))

    # Import after setting env so RULES_PATH is picked up
    api = importlib.import_module("src.api")
    importlib.reload(api)

    client = TestClient(api.app)

    # List empty
    r = client.get("/rules")
    assert r.status_code == 200
    assert r.json() == []

    # Add rule
    rule = {
        "id": "r1",
        "target": "column",
        "selector": "dbo.Customers.Phone",
        "action": "autocorrect",
        "reason": "Normalize SE phone",
        "confidence": 0.9,
    }
    r = client.post("/rules", json=rule)
    assert r.status_code == 200
    assert r.json()["id"] == "r1"

    # List again
    r = client.get("/rules")
    assert len(r.json()) == 1

    # Delete
    r = client.delete("/rules/r1")
    assert r.status_code == 200
    assert r.json()["deleted"] == "r1"

