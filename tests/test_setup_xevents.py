from scripts.setup_xevents import render_xevents_sql
import importlib
import pytest


def test_render_xevents_contains_targets():
    ring = render_xevents_sql("ring")
    assert "ring_buffer" in ring and "CREATE EVENT SESSION [sqlumai_capture]" in ring
    fil = render_xevents_sql("file")
    assert "event_file" in fil and "sql_batch_completed" in fil


def test_xevents_setup_api_optional(tmp_path, monkeypatch):
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "rules.json"))
    try:
        api = importlib.import_module("src.api")
    except ModuleNotFoundError:
        pytest.skip("fastapi not installed; skipping API test")
    importlib.reload(api)
    res = api.xevents_setup(mode="ring")
    assert "sql" in res and "CREATE EVENT SESSION" in res["sql"]
