from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import json
import os
from threading import RLock
from src.metrics import store as metrics_store
from src.metrics import decisions as decisions_store

app = FastAPI(title="SQLumAI Policy API", version="0.1.0")

RULES_PATH = os.getenv("RULES_PATH", "config/rules.json")
_lock = RLock()


class Rule(BaseModel):
    id: str = Field(..., description="Unique rule identifier")
    target: Literal["table", "column", "pattern"]
    selector: str = Field(..., description="e.g., dbo.Table.Col or LIKE pattern")
    action: Literal["allow", "block", "autocorrect"]
    reason: str = ""
    confidence: float = 1.0
    enabled: bool = True
    apply_in_envs: Optional[List[str]] = Field(default=None, description="List of environments where this rule applies")
    min_hits_to_enforce: int = 0  # When ENFORCEMENT_MODE=enforce, require this many dry-run hits before enforcing


def _read_rules() -> List[Rule]:
    with _lock:
        if not os.path.exists(RULES_PATH):
            return []
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [Rule(**r) for r in data]


def _write_rules(rules: List[Rule]):
    with _lock:
        os.makedirs(os.path.dirname(RULES_PATH) or ".", exist_ok=True)
        with open(RULES_PATH, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in rules], f, indent=2)


@app.get("/rules", response_model=List[Rule])
def list_rules():
    return _read_rules()


@app.post("/rules", response_model=Rule)
def add_rule(rule: Rule):
    rules = _read_rules()
    if any(r.id == rule.id for r in rules):
        raise HTTPException(status_code=409, detail="Rule id exists")
    rules.append(rule)
    _write_rules(rules)
    return rule


@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: str):
    rules = _read_rules()
    new_rules = [r for r in rules if r.id != rule_id]
    if len(new_rules) == len(rules):
        raise HTTPException(status_code=404, detail="Not found")
    _write_rules(new_rules)
    return {"deleted": rule_id}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return metrics_store.get_all()


@app.get("/decisions")
def decisions(limit: int = 50):
    return decisions_store.tail(limit)


@app.get("/metrics.html")
def metrics_html(limit: int = 50):
    metrics = metrics_store.get_all()
    decs = decisions_store.tail(limit)
    # Simple HTML rendering
    rows = "".join(
        f"<tr><td>{d.get('ts','')}</td><td>{d.get('action','')}</td><td>{d.get('rule_id','')}</td><td>{(d.get('reason','') or '')[:120]}</td></tr>"
        for d in decs
    )
    html = f"""
    <html><head><title>SQLumAI Metrics</title><style>body{{font-family:Arial,sans-serif}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:4px}}</style></head>
    <body>
      <h1>Metrics</h1>
      <ul>
        {''.join(f'<li><b>{k}</b>: {v}</li>' for k,v in metrics.items())}
      </ul>
      <h2>Recent Decisions (last {limit})</h2>
      <table>
        <tr><th>Time (UTC)</th><th>Action</th><th>Rule</th><th>Reason</th></tr>
        {rows}
      </table>
    </body></html>
    """
    return html


@app.get("/dryrun.html")
def dryrun_html(rule: str | None = None, action: str | None = None, date: str | None = None):
    # Aggregate decisions by rule and action for today
    import datetime as dt
    day = (date or dt.datetime.utcnow().date().isoformat())
    all_decs = decisions_store.tail(5000)
    agg = {}
    for d in all_decs:
        ts = d.get("ts", "")
        if not ts.startswith(day):
            continue
        rid = d.get("rule_id") or "(no_rule)"
        act = (d.get("action") or "").lower()
        if rule and rid != rule:
            continue
        if action and act != action:
            continue
        agg.setdefault(rid, {}).setdefault(act, 0)
        agg[rid][act] += 1
    rows = "".join(f"<tr><td>{rid}</td><td>{', '.join(f'{k}:{v}' for k,v in acts.items())}</td></tr>" for rid, acts in agg.items())
    html = f"""
    <html><head><title>Dry‑Run Dashboard</title><style>body{{font-family:Arial,sans-serif}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:4px}}</style></head>
    <body>
      <h1>Dry‑Run Dashboard – {day}</h1>
      <form method="get" style="margin-bottom:10px;">
        Rule: <input type="text" name="rule" value="{rule or ''}" />
        Action: <input type="text" name="action" value="{action or ''}" />
        Date (YYYY-MM-DD): <input type="text" name="date" value="{day}" />
        <button type="submit">Filter</button>
      </form>
      <table>
        <tr><th>Rule</th><th>Counts by Action</th></tr>
        {rows}
      </table>
    </body></html>
    """
    return html


@app.get("/dryrun.json")
def dryrun_json(rule: str | None = None, action: str | None = None, date: str | None = None):
    import datetime as dt
    day = (date or dt.datetime.utcnow().date().isoformat())
    all_decs = decisions_store.tail(10000)
    agg = {}
    for d in all_decs:
        ts = d.get("ts", "")
        if not ts.startswith(day):
            continue
        rid = d.get("rule_id") or "(no_rule)"
        act = (d.get("action") or "").lower()
        if rule and rid != rule:
            continue
        if action and act != action:
            continue
        agg.setdefault(rid, {}).setdefault(act, 0)
        agg[rid][act] += 1
    return {"date": day, "rules": agg}
