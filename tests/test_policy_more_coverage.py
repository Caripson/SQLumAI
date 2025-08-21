import importlib
import json
import sys
import types
import pytest


def setup_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    monkeypatch.setenv("PROPOSED_RULES_PATH", str(tmp_path / "rules_proposed.json"))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    return api


def test_policy_engine_env_and_enabled():
    from src.policy.engine import PolicyEngine, Event, Rule

    rules = [
        Rule(id="skip-env", target="table", selector="dbo.Env", action="block", reason="env", enabled=True),
        Rule(id="only-dev", target="table", selector="dbo.Dev", action="block", reason="env", enabled=True),
        Rule(id="disabled", target="table", selector="dbo.Off", action="block", reason="off", enabled=False),
    ]
    # Attach apply_in_envs dynamically to simulate Pydantic model fields
    setattr(rules[1], "apply_in_envs", ["dev"])  # only in dev

    pe = PolicyEngine(rules, environment="prod")
    # 'skip-env' not restricted by env, so it can match
    d1 = pe.decide(Event(None, None, None, "dbo.Env", None, None))
    assert d1.rule_id == "skip-env"
    # 'only-dev' is restricted to dev and should be skipped in prod
    d2 = pe.decide(Event(None, None, None, "dbo.Dev", None, None))
    assert d2.rule_id != "only-dev"
    # 'disabled' should never match
    d3 = pe.decide(Event(None, None, None, "dbo.Off", None, None))
    assert d3.rule_id != "disabled"


def test_metrics_prom_success_branch(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    # Provide a fake prometheus_client with required symbols
    fake = types.SimpleNamespace(
        generate_latest=lambda: b"metric 1\n",
        CONTENT_TYPE_LATEST="text/plain; version=0.0.4; charset=utf-8",
    )
    monkeypatch.setitem(sys.modules, "prometheus_client", fake)  # type: ignore[arg-type]
    resp = api.metrics_prom()
    # In shim Response, .content is set
    content = getattr(resp, "content", b"")
    assert b"metric 1" in content or "metric 1" in str(content)


def test_rules_delete_success(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    r = api.Rule(id="del", target="table", selector="dbo.X", action="allow")
    api.add_rule(r)
    out = api.delete_rule("del")
    assert out.get("deleted") == "del"


def test_proposed_duplicate_conflict(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    r = api.Rule(id="dup", target="pattern", selector="INSERT", action="block")
    api.add_rule_proposed(r)
    with pytest.raises(api.HTTPException) as ei:
        api.add_rule_proposed(r)
    assert getattr(ei.value, "status_code", 0) == 409


def test_rules_diff_changed(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    cur = [api.Rule(id="same", target="table", selector="dbo.T", action="allow")]
    prop = [api.Rule(id="same", target="table", selector="dbo.T2", action="allow")]
    (tmp_path / "rules.json").write_text(json.dumps([r.model_dump() for r in cur]), encoding="utf-8")
    (tmp_path / "rules_proposed.json").write_text(json.dumps([r.model_dump() for r in prop]), encoding="utf-8")
    diff = api.rules_diff()
    assert any(d.get("id") == "same" for d in diff.get("changed", []))


def test_rules_test_default_path(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    # No rules -> should allow by default
    ev = api._TestEvent(table="dbo.Nope", column=None, value=None, sql_text=None)
    out = api.rules_test(ev)
    assert out.get("action") == "allow"
