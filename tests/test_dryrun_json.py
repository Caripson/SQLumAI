import json
import datetime as dt
import importlib


def test_dryrun_json_aggregation(tmp_path, monkeypatch):
    # Prepare decisions for today
    d = tmp_path / 'data/metrics'
    d.mkdir(parents=True)
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    items = [
        {"ts": today + 'T01:00:00Z', "rule_id": "r1", "action": "autocorrect"},
        {"ts": today + 'T02:00:00Z', "rule_id": "r1", "action": "block"},
        {"ts": today + 'T03:00:00Z', "rule_id": "r2", "action": "allow"},
    ]
    (d / 'decisions.jsonl').write_text('\n'.join(json.dumps(x) for x in items), encoding='utf-8')

    monkeypatch.chdir(tmp_path)
    # Ensure decisions module points to current cwd path
    import src.metrics.decisions as dec
    importlib.reload(dec)
    api = importlib.import_module('src.api')
    importlib.reload(api)
    out = api.dryrun_json(date=today)
    assert out['date'] == today
    assert 'r1' in out['rules']
