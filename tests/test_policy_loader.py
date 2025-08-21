import json
from src.policy.loader import load_rules


def test_load_rules_skips_invalid(tmp_path, monkeypatch):
    p = tmp_path / "rules.json"
    data = [
        {"id": "ok1", "target": "table", "selector": "dbo.T", "action": "allow"},
        {"id": "bad", "target": "invalid", "selector": 123, "action": "noop"},
        {"id": "ok2", "target": "column", "selector": "dbo.T.Email", "action": "block"},
    ]
    p.write_text(json.dumps(data), encoding="utf-8")
    rs = load_rules(str(p))
    ids = [r.id for r in rs]
    assert "ok1" in ids and "ok2" in ids and all(x != "bad" for x in ids)

