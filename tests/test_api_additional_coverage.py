import importlib
import os
import json
import pytest


def setup_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    monkeypatch.setenv("PROPOSED_RULES_PATH", str(tmp_path / "rules_proposed.json"))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    return api


def test_rules_ui_and_test_endpoint(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    # Add a simple rule to render in UI
    r = api.Rule(id="r-ui", target="table", selector="dbo.T", action="allow")
    api.add_rule(r)
    html = api.rules_ui()
    assert "<h1>Rules</h1>" in html and "r-ui" in html

    # Exercise rules_test endpoint path
    ev = api._TestEvent(table="dbo.T", column=None, value=None, sql_text="SELECT 1")
    out = api.rules_test(ev)
    assert isinstance(out, dict) and "action" in out


def test_proposed_rules_flow(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)

    # Proposed list is empty
    assert api.list_rules_proposed() == []

    # Add a proposed rule
    pr = api.Rule(id="p1", target="pattern", selector="INSERT INTO", action="block")
    api.add_rule_proposed(pr)
    assert any(r.id == "p1" for r in api.list_rules_proposed())

    # Add current rule set to compare diff
    cur = [api.Rule(id="c1", target="table", selector="dbo.T", action="allow")]
    # Write current rules to RULES_PATH
    with open(os.environ["RULES_PATH"], "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in cur], f)

    diff = api.rules_diff()
    assert any(item.get("id") == "p1" for item in diff.get("added", []))

    # Promote proposed -> current
    res = api.rules_promote()
    assert res.get("promoted", 0) >= 1


def test_xevents_setup_modes_and_invalid(monkeypatch):
    api = importlib.import_module("src.api")
    importlib.reload(api)
    ok_ring = api.xevents_setup("ring")
    ok_file = api.xevents_setup("file")
    assert "sql" in ok_ring and "sql" in ok_file
    with pytest.raises(api.HTTPException) as ei:
        api.xevents_setup("badmode")
    assert getattr(ei.value, "status_code", 0) == 400


def test_rules_suggest_variants(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    r1 = api.rules_suggest(api._SuggestReq(text="Please normalize phone numbers"))
    assert isinstance(r1, dict) and r1.get("target") in ("column", "pattern")
    r2 = api.rules_suggest(api._SuggestReq(text="Email must be required"))
    assert r2.get("id") in ("no-null-email", "suggest-1")

