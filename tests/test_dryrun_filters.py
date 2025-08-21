import importlib
import json
import datetime as dt


def test_dryrun_html_filters(tmp_path, monkeypatch):
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    d = tmp_path / 'data/metrics'
    d.mkdir(parents=True)
    rows = [
        {"ts": today + 'T01:00:00Z', "rule_id": "r1", "action": "block"},
        {"ts": today + 'T02:00:00Z', "rule_id": "r2", "action": "autocorrect"},
    ]
    (d / 'decisions.jsonl').write_text('\n'.join(json.dumps(x) for x in rows), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    api = importlib.import_module('src.api')
    importlib.reload(api)
    html = api.dryrun_html(rule='r1', action='block', date=today)
    assert 'r1' in html and 'r2' not in html
