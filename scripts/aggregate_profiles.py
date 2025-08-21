#!/usr/bin/env python3
"""Aggregates raw XEvent JSONL into simple field profiles and suggestions.
Outputs data/aggregations/field_profiles.json
"""
import json
from collections import defaultdict, Counter
from pathlib import Path
import re
from agents.normalizers import suggest_normalizations
from src.tds.sqlparse_simple import extract_select_info


RAW_DIR = Path("data/xevents/raw")
OUT_FILE = Path("data/aggregations/field_profiles.json")


def iter_events():
    if not RAW_DIR.exists():
        return []
    for p in sorted(RAW_DIR.glob("*.jsonl")):
        with p.open() as f:
            for line in f:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def extract_columns(sql_text: str):
    # Simple regex-based extraction for INSERT/UPDATE
    if not sql_text:
        return []
    m = re.search(r"insert\s+into\s+([\w\.\[\]]+)\s*\(([^\)]+)\)" , sql_text, re.IGNORECASE)
    cols = []
    if m:
        table = m.group(1)
        columns = [c.strip(" []") for c in m.group(2).split(",")]
        for c in columns:
            cols.append((table, c))
    m2 = re.search(r"update\s+([\w\.\[\]]+)\s+set\s+(.+?)\s+where\s", sql_text, re.IGNORECASE | re.DOTALL)
    if m2:
        table = m2.group(1)
        assigns = m2.group(2)
        for part in assigns.split(","):
            left = part.split("=")[0].strip(" []")
            cols.append((table, left))
    return cols


def extract_values(sql_text: str):
    # Try to capture values from INSERT ... VALUES (...)
    vals = []
    m = re.search(r"insert\s+into\s+[\w\.\[\]]+\s*\(([^\)]+)\)\s*values\s*\(([^\)]+)\)", sql_text, re.IGNORECASE | re.DOTALL)
    if m:
        columns = [c.strip(" []") for c in m.group(1).split(",")]
        raw_vals = [v.strip() for v in m.group(2).split(",")]
        for c, v in zip(columns, raw_vals):
            # Strip quotes
            if v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            vals.append((c, v))
    # UPDATE ... SET col = value
    m2 = re.search(r"update\s+[\w\.\[\]]+\s+set\s+(.+?)\s+where\s", sql_text, re.IGNORECASE | re.DOTALL)
    if m2:
        assigns = m2.group(1)
        for part in assigns.split(","):
            if "=" in part:
                left, right = part.split("=", 1)
                c = left.strip(" []")
                v = right.strip()
                if v.startswith("'") and v.endswith("'"):
                    v = v[1:-1]
                vals.append((c, v))
    return vals


def main():
    profiles = defaultdict(lambda: {"count": 0, "nulls": 0, "values": Counter(), "suggestions": Counter()})
    select_summary = defaultdict(lambda: {"star": 0, "columns": Counter()})
    for e in iter_events():
        sql_text = (e.get("sql_text") or "").strip()
        cols = extract_columns(sql_text)
        # Build table prefix for values if possible (take first table)
        table = cols[0][0] if cols else None
        values = extract_values(sql_text)
        for table_name, col in cols:
            key = f"{table_name}.{col}"
            profiles[key]["count"] += 1
        # Try to map values to columns for normalization suggestions
        if table and values:
            for col, val in values:
                key = f"{table}.{col}"
                suggestion = suggest_normalizations(val)
                if suggestion:
                    kind = suggestion["kind"]
                    profiles[key]["suggestions"][kind] += 1

        # Read-only SELECT analysis (lightweight): count SELECT * and column usage
        if sql_text.lower().startswith("select "):
            tables, cols_sel, star = extract_select_info(sql_text)
            if tables:
                t = tables[0]
                if star:
                    select_summary[t]["star"] += 1
                for c in cols_sel:
                    select_summary[t]["columns"][c] += 1

    # Convert Counters to plain dicts
    out = {k: {**v, "values": dict(v["values"]), "suggestions": dict(v["suggestions"])} for k, v in profiles.items()}
    select_out = {k: {"star": v["star"], "columns": dict(v["columns"])} for k, v in select_summary.items()}
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump({"profiles": out, "selects": select_out}, f, indent=2)
    print(f"Wrote profiles to {OUT_FILE}")


if __name__ == "__main__":
    main()
