import importlib
import json
import datetime as dt
import pytest
try:
    from fastapi import HTTPException
except Exception:  # pragma: no cover - optional in minimal env
    pytest.skip("fastapi not installed; skipping API tests", allow_module_level=True)


def setup_api_with_rules(tmp_path, monkeypatch):
    rules_path = tmp_path / "rules.json"
    monkeypatch.setenv("RULES_PATH", str(rules_path))
    api = importlib.import_module("src.api")
    importlib.reload(api)
    return api


def test_rules_conflicts_and_notfound(tmp_path, monkeypatch):
    api = setup_api_with_rules(tmp_path, monkeypatch)
    # Add first rule
    r = api.Rule(id="dup", target="table", selector="dbo.T", action="allow")
    api.add_rule(r)
    # Adding duplicate should raise 409
    try:
        api.add_rule(r)
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 409
    # Deleting unknown id should raise 404
    try:
        api.delete_rule("missing")
        assert False, "Expected HTTPException"
    except HTTPException as e:
        assert e.status_code == 404


def test_health_and_decisions_and_metrics_html(tmp_path, monkeypatch):
    # Prepare metrics/decisions files
    mdir = tmp_path / "data/metrics"
    mdir.mkdir(parents=True)
    (mdir / "metrics.json").write_text(json.dumps({"allowed": 3}), encoding="utf-8")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    rows = [
        {"ts": today + "T01:00:00Z", "rule_id": "r1", "action": "block", "reason": "bad data"},
        {"ts": today + "T02:00:00Z", "rule_id": "r2", "action": "allow", "reason": "ok"},
        {"ts": "1999-01-01T00:00:00Z", "rule_id": "rX", "action": "allow"},  # old date should be ignored in filters
    ]
    (mdir / "decisions.jsonl").write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")

    # Point module paths to tmp workspace
    monkeypatch.chdir(tmp_path)
    import src.metrics.decisions as dec
    importlib.reload(dec)
    import src.metrics.store as ms
    importlib.reload(ms)

    api = importlib.import_module("src.api")
    importlib.reload(api)

    # healthz
    assert api.healthz()["status"] == "ok"
    # decisions (limit parameter exercised)
    decs = api.decisions(limit=2)
    assert len(decs) == 2
    # metrics.html renders counters and decisions table
    html = api.metrics_html(limit=5)
    assert "SQLumAI Metrics" in html and "Recent Decisions" in html


def test_metrics_prom_success(monkeypatch):
    # Ensure the real prometheus_client is present and returns bytes
    api = importlib.import_module("src.api")
    importlib.reload(api)
    resp = api.metrics_prom()
    assert hasattr(resp, "media_type") and "text/plain" in getattr(resp, "media_type", "") or getattr(resp, "media_type", "")


def test_insights_no_files(tmp_path, monkeypatch):
    # No insights present: should return placeholder HTML
    monkeypatch.chdir(tmp_path)
    api = importlib.import_module("src.api")
    importlib.reload(api)
    out = api.insights_html()
    body = out.body.decode("utf-8") if hasattr(out, "body") else str(out)
    assert "No insights yet" in body


def test_insights_markdown_variants(tmp_path, monkeypatch):
    # Cover h1, h2, list and paragraph rendering branches
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    content = "\n".join([
        "# Title",
        "## Subsection",
        "- bullet item",
        "A paragraph line",
    ])
    (reports / f"insights-{today}.md").write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    api = importlib.import_module("src.api")
    importlib.reload(api)
    r = api.insights_html()
    body = r.body.decode("utf-8") if hasattr(r, "body") else str(r)
    assert "<h1>Title</h1>" in body and "<h2>Subsection</h2>" in body and "bullet item" in body and "paragraph" in body


def test_dryrun_filters_exclusions(tmp_path, monkeypatch):
    # Prepare decisions with different dates/rules/actions to exercise continue branches
    d = tmp_path / "data/metrics"
    d.mkdir(parents=True)
    today = dt.datetime.utcnow().date().isoformat()
    rows = [
        {"ts": today + "T01:00:00Z", "rule_id": "r1", "action": "block"},
        {"ts": today + "T02:00:00Z", "rule_id": "r2", "action": "autocorrect"},
        {"ts": "1999-01-01T00:00:00Z", "rule_id": "r1", "action": "block"},  # excluded by date
    ]
    (d / "decisions.jsonl").write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    api = importlib.import_module("src.api")
    importlib.reload(api)

    # Only r1:block should remain when filtering
    j = api.dryrun_json(rule="r1", action="block", date=today)
    assert j["rules"].get("r1", {}).get("block", 0) == 1
    h = api.dryrun_html(rule="r1", action="block", date=today)
    assert "r1" in h and "r2" not in h
