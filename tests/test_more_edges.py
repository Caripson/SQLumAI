import importlib
import json


def test_store_read_corrupt_and_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Corrupt metrics file -> get_all returns {}
    mdir = tmp_path / "data/metrics"
    mdir.mkdir(parents=True)
    (mdir / "metrics.json").write_text("not-json", encoding="utf-8")
    import src.metrics.store as store
    importlib.reload(store)
    assert store.get_all() == {}
    # Decisions missing file -> tail returns []
    import src.metrics.decisions as dec
    importlib.reload(dec)
    assert dec.tail(5) == []


def test_loader_skips_on_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bad = [
        {"id": "ok", "target": "table", "selector": "dbo.T", "action": "allow"},
        {"id": "oops", "target": "table", "selector": "dbo.X", "action": "block", "unknown": 1},
    ]
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config/rules.json").write_text(json.dumps(bad), encoding="utf-8")
    from src.policy.loader import load_rules
    out = load_rules(str(tmp_path / "config/rules.json"))
    ids = [r.id for r in out]
    assert ids == ["ok"]


def test_api_metrics_html_no_decs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Prepare metrics only
    mdir = tmp_path / "data/metrics"
    mdir.mkdir(parents=True)
    (mdir / "metrics.json").write_text(json.dumps({"allowed": 1}), encoding="utf-8")
    api = importlib.import_module("src.api")
    importlib.reload(api)
    html = api.metrics_html(limit=3)
    assert "Metrics" in html and "Recent Decisions" in html


def test_dryrun_json_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    api = importlib.import_module("src.api")
    importlib.reload(api)
    out = api.dryrun_json()
    assert isinstance(out, dict) and isinstance(out.get("rules"), dict) and len(out.get("rules")) == 0


def test_rules_list_add_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    assert api.list_rules() == []
    r = api.Rule(id="a1", target="table", selector="dbo.T", action="allow")
    api.add_rule(r)
    assert any(x.id == "a1" for x in api.list_rules())

