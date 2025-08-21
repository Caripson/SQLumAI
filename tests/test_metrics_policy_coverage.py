import importlib
import json
import sys
from types import ModuleType


def test_metrics_store_inc_and_rule_counters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import src.metrics.store as store
    importlib.reload(store)

    store.inc("allowed", 2)
    store.inc_rule_action("r1", "block", 3)
    data = store.get_all()
    assert data.get("allowed") == 2 and data.get("rule:r1:block") == 3
    rc = store.get_rule_counters("r1")
    assert rc == {"block": 3}


def test_decisions_append_and_tail_limit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import src.metrics.decisions as dec
    importlib.reload(dec)
    dec.append({"action": "allow", "rule_id": "rA"})
    dec.append({"action": "block", "rule_id": "rB"})
    # Inject a bad line
    p = tmp_path / "data/metrics/decisions.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + "bad\n", encoding="utf-8")
    items = dec.tail(limit=3)
    assert any(it.get("rule_id") == "rB" for it in items)
    assert all("ts" in it for it in items if isinstance(it, dict))


def test_policy_loader_valid_and_invalid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rules = [
        {"id": "v1", "target": "table", "selector": "dbo.T", "action": "allow"},
        {"id": "bad-tgt", "target": "xxx", "selector": "dbo.T", "action": "allow"},
        {"id": "bad-act", "target": "table", "selector": "dbo.T", "action": "noop"},
        {"id": "bad-sel", "target": "table", "selector": None, "action": "block"},
    ]
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/rules.json").write_text(json.dumps(rules), encoding="utf-8")
    from src.policy.loader import load_rules
    out = load_rules(str(tmp_path / "config/rules.json"))
    assert [r.id for r in out] == ["v1"]


def test_policy_engine_matching_and_env():
    from src.policy.engine import PolicyEngine, Event, Rule

    rules = [
        Rule(id="t", target="table", selector="dbo.T", action="block", reason="tbl"),
        Rule(id="c1", target="column", selector="Email", action="autocorrect", reason="col"),
        Rule(id="p", target="pattern", selector="INSERT INTO", action="block", reason="pat"),
        Rule(id="env", target="table", selector="dbo.Env", action="block", reason="env", enabled=True),
    ]
    pe = PolicyEngine(rules, environment="prod")
    # table match
    d1 = pe.decide(Event(database=None, user=None, sql_text=None, table="dbo.T", column=None, value=None))
    assert d1.action == "block" and d1.rule_id == "t"
    # column-only match matches both dotted and parameter forms
    d2 = pe.decide(Event(None, None, None, None, "dbo.Users.Email", None))
    d3 = pe.decide(Event(None, None, None, None, "@Email", None))
    assert d2.action == d3.action == "autocorrect"
    # pattern match
    d4 = pe.decide(Event(None, None, "insert into dbo.x values(1)", None, None, None))
    assert d4.rule_id == "p"
    # get_rule
    assert pe.get_rule("t").id == "t"


def test_metrics_prom_fallback_lines(tmp_path, monkeypatch):
    # Force fallback path by inserting a dummy prometheus_client without required symbols
    dummy = ModuleType("prometheus_client")
    monkeypatch.setitem(sys.modules, "prometheus_client", dummy)
    monkeypatch.chdir(tmp_path)
    # Prepare metrics
    mdir = tmp_path / "data/metrics"
    mdir.mkdir(parents=True)
    (mdir / "metrics.json").write_text(json.dumps({"allowed": 5, "rule:rX:block": 2}), encoding="utf-8")

    api = importlib.import_module("src.api")
    importlib.reload(api)
    resp = api.metrics_prom()
    payload = getattr(resp, "body", None) or getattr(resp, "content", None) or resp
    text = payload.decode("utf-8") if hasattr(payload, "decode") else str(payload)
    assert "sqlumai_metric{key=\"allowed\"} 5" in text
    assert "sqlumai_metric{key=\"rule\",rule=\"rX\",action=\"block\"} 2" in text
