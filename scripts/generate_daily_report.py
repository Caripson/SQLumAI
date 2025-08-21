#!/usr/bin/env python3
import json
from pathlib import Path
import datetime as dt

PROFILES = Path("data/aggregations/field_profiles.json")
REPORTS_DIR = Path("reports")


def main():
    if not PROFILES.exists():
        raise SystemExit("No profiles found. Run scripts/aggregate_profiles.py first.")
    raw = json.loads(PROFILES.read_text())
    # Backward compatible: either a flat mapping or a dict with 'profiles' and 'selects'
    if isinstance(raw, dict) and "profiles" in raw:
        profiles = raw.get("profiles", {})
        selects = raw.get("selects", {})
    else:
        profiles = raw
        selects = {}

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
    if selects:
        lines.append("## SELECT Analysis")
        for table, info in selects.items():
            star = info.get("star", 0)
            cols = sorted(info.get("columns", {}).items(), key=lambda kv: kv[1], reverse=True)[:5]
            cols_str = ", ".join(f"{c}:{n}" for c, n in cols)
            lines.append(f"- {table}: select_star={star}, top_columns=[{cols_str}]")
        lines.append("")
    lines.append("## Drift & Errors")
    # Optional: compute simple null-ratio drift if previous snapshot is available
    prev_path = PROFILES.with_name("field_profiles.prev.json")
    if prev_path.exists():
        from scripts.drift_utils import compute_null_drift
        prev_raw = json.loads(prev_path.read_text())
        prev_profiles = prev_raw.get("profiles", prev_raw) if isinstance(prev_raw, dict) else {}
        drifts = compute_null_drift(prev_profiles, profiles, threshold=0.1)[:10]
        for field, delta in drifts:
            lines.append(f"- {field}: null_ratio drift {delta:.2f}")
    else:
        lines.append("- TODO: compute PSI/KL and error trends once enough history is available.")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote report to {out}")


if __name__ == "__main__":
    main()
