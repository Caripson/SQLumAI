import importlib
import pytest


def test_rules_suggest_stub(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    try:
        api = importlib.import_module("src.api")
    except ModuleNotFoundError:
        pytest.skip("fastapi not installed; skipping suggest test")
    importlib.reload(api)
    out = api.rules_suggest(api._SuggestReq(text="Alla svenska telefonnummer ska normaliseras"))
    assert out["target"] in ("column", "pattern") and out["action"] in ("autocorrect", "block", "allow")
