import importlib
import pytest


def setup_api(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    try:
        api = importlib.import_module("src.api")
    except ModuleNotFoundError:
        pytest.skip("fastapi not installed; skipping UI tests")
    importlib.reload(api)
    return api


def test_rules_ui_renders(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    html = api.rules_ui()
    assert "Rules UI" in html and "Add Rule" in html and "Test Decision" in html


def test_rules_test_endpoint(tmp_path, monkeypatch):
    api = setup_api(tmp_path, monkeypatch)
    # No rules -> allow
    res = api.rules_test(api._TestEvent(table="dbo.T", column="dbo.T.Email", value="x"))
    assert res["action"] == "allow"
    # Add a block rule on Email
    r = api.Rule(id="b1", target="column", selector="dbo.T.Email", action="block", reason="required")
    api.add_rule(r)
    res2 = api.rules_test(api._TestEvent(table="dbo.T", column="dbo.T.Email", value=""))
    assert res2["action"] == "block" and res2["rule_id"] == "b1"
