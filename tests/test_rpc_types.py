import json
from src.tds.rpc_types import load_param_types


def test_load_param_types_ok_and_missing(tmp_path, monkeypatch):
    p = tmp_path / "types.json"
    p.write_text(json.dumps({"dbo.proc": {"@Name": "NVARCHAR", "id": "INT"}}), encoding="utf-8")
    d = load_param_types(str(p))
    assert d.get("dbo.proc", {}).get("name") == "NVARCHAR" and d["dbo.proc"].get("id") == "INT"
    # missing
    assert load_param_types(str(tmp_path / "no.json")) == {}

