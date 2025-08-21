import importlib


def test_tail_missing_and_garbage(tmp_path, monkeypatch):
    # Missing file returns empty list
    monkeypatch.setenv("DECISIONS_PATH", str(tmp_path / "nope.jsonl"))
    dec = importlib.import_module("src.metrics.decisions")
    importlib.reload(dec)
    assert dec.tail(5) == []

    # Invalid JSON lines are skipped without crashing
    p = tmp_path / "decisions.jsonl"
    p.write_text("{not json}\n{\"ts\": \"2020-01-01T00:00:00Z\", \"action\": \"allow\"}", encoding="utf-8")
    monkeypatch.setenv("DECISIONS_PATH", str(p))
    importlib.reload(dec)
    out = dec.tail(10)
    assert isinstance(out, list) and len(out) == 1

