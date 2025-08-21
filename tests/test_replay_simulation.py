import json
from pathlib import Path
from scripts.replay_dryrun import simulate, write_report


def test_simulate_and_write_report(tmp_path, monkeypatch):
    # Prepare rules file
    rules_path = tmp_path / "rules.json"
    rules = [{"id": "block-email", "target": "column", "selector": "dbo.T.Email", "action": "block"}]
    rules_path.write_text(json.dumps(rules), encoding="utf-8")
    # Prepare events JSONL
    ev_path = tmp_path / "events.jsonl"
    lines = [
        {"table": "dbo.T", "column": "dbo.T.Email", "value": "", "sql_text": "UPDATE dbo.T SET Email='' WHERE Id=1"},
        {"table": "dbo.T", "column": "dbo.T.Phone", "value": "+4612345678", "sql_text": "INSERT INTO dbo.T (Phone) VALUES ('+4612345678')"},
    ]
    ev_path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    res = simulate(ev_path, str(rules_path))
    assert res["actions"].get("block", 0) >= 1
    # Write report
    out = write_report(res)
    assert out.exists() and out.read_text().startswith("# Dry‑Run Simulation")

