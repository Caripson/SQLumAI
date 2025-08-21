import importlib
import datetime as dt


def test_insights_html_renders(tmp_path, monkeypatch):
    # Arrange: create a dummy insights report for today
    today = dt.datetime.utcnow().date().isoformat()
    reports = tmp_path / 'reports'
    reports.mkdir(parents=True)
    (reports / f'insights-{today}.md').write_text('# Insights\n\n- Sample insight', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    # Act: import api and call /insights.html
    api = importlib.import_module('src.api')
    importlib.reload(api)
    r = api.insights_html()

    # Assert
    assert 'Sample insight' in r.body.decode('utf-8')  # type: ignore[attr-defined]
