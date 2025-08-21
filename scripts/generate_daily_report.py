#!/usr/bin/env python3
import json
from pathlib import Path
import datetime as dt

PROFILES = Path("data/aggregations/field_profiles.json")
REPORTS_DIR = Path("reports")


def main():
    if not PROFILES.exists():
        raise SystemExit("No profiles found. Run scripts/aggregate_profiles.py first.")
    profiles = json.loads(PROFILES.read_text())

    # Simple rankings
    top_fields = sorted(profiles.items(), key=lambda kv: kv[1].get("nulls", 0), reverse=True)[:10]
    top_suggestions = sorted(
        ((k, sum(v.get("suggestions", {}).values())) for k, v in profiles.items()), key=lambda kv: kv[1], reverse=True
    )[:10]

    date = dt.datetime.utcnow().strftime("%Y-%m-%d")
    REPORTS_DIR.mkdir(exist_ok=True)
    out = REPORTS_DIR / f"report-{date}.md"

    lines = [
        f"# Daily Data Quality Report – {date}",
        "",
        "## Top Missingness",
    ]
    for k, v in top_fields:
        lines.append(f"- {k}: nulls={v.get('nulls',0)} / count={v.get('count',0)}")
    lines.append("")
    lines.append("## Format Issues & Suggestions")
    for k, n in top_suggestions:
        kinds = profiles[k].get("suggestions", {})
        hints = ", ".join(f"{kind}:{cnt}" for kind, cnt in kinds.items())
        lines.append(f"- {k}: {n} suggestions ({hints})")
    lines.append("")
    lines.append("## Drift & Errors")
    lines.append("- TODO: compute PSI/KL and error trends once enough history is available.")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {out}")


if __name__ == "__main__":
    main()
