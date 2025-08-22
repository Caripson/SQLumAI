import os
import json
import datetime as dt
import importlib


def test_e2e_reports_and_api(tmp_path, monkeypatch):
    # Prepare profiles
    data_dir = tmp_path / "data/aggregations"
    data_dir.mkdir(parents=True)
    profiles = {
        "dbo.Users.Email": {"count": 10, "nulls": 2, "suggestions": {"email": 3}},
        "dbo.Customers.Phone": {"count": 5, "nulls": 0, "suggestions": {"phone": 2}},
    }
    (data_dir / "field_profiles.json").write_text(json.dumps(profiles), encoding="utf-8")

    # Decisions for today
    dec_dir = tmp_path / "data/metrics"
    dec_dir.mkdir(parents=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    decs = [
        {"ts": today + "T00:00:00Z", "action": "autocorrect", "rule_id": "r-email", "reason": "Normalize email", "sample": "INSERT ..."},
        {"ts": today + "T00:05:00Z", "action": "block", "rule_id": "r-block", "reason": "Block test data", "sample": "INSERT ..."},
    ]
    (dec_dir / "decisions.jsonl").write_text("\n".join(json.dumps(d) for d in decs), encoding="utf-8")

    # Reports out
    rep_dir = tmp_path / "reports"
    rep_dir.mkdir(parents=True)

    # Point scripts to tmp workspace
    monkeypatch.chdir(tmp_path)

    # Generate reports
    import scripts.generate_daily_report as daily
    import scripts.generate_dryrun_report as dry
    import scripts.llm_summarize_profiles as llm

    importlib.reload(daily)
    importlib.reload(dry)
    importlib.reload(llm)
    daily.main()
    dry.main()
    llm.main()

    # Verify files
    assert any(p.name.startswith("report-") for p in rep_dir.iterdir())
    assert any(p.name.startswith("dryrun-") for p in rep_dir.iterdir())
    assert any(p.name.startswith("llm-summary-") for p in rep_dir.iterdir())

    # API: metrics and dryrun
    os.environ["RULES_PATH"] = str(tmp_path / "config/rules.json")
    api = importlib.import_module("src.api")
    importlib.reload(api)
    # Call functions directly to avoid TestClient in restricted env
    m = api.metrics()
    assert isinstance(m, dict)
    html = api.dryrun_html()
    assert "Dry‑Run Dashboard" in html
