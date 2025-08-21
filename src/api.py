try:
    from fastapi import FastAPI, HTTPException, Response
except Exception:  # minimal shim for environments without fastapi
    class HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: str = ""):
            super().__init__(detail)
            self.status_code = status_code

    class Response:  # type: ignore
        def __init__(self, content: str | bytes = b"", media_type: str = "text/html"):
            self.content = content
            self.media_type = media_type
            # For tests accessing body
            try:
                self.body = content if isinstance(content, bytes) else str(content).encode("utf-8")
            except Exception:
                self.body = b""

    class DummyApp:
        def __init__(self, *_, **__):
            pass

        def get(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco

        def post(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco

        def delete(self, *_args, **_kwargs):
            def deco(fn):
                return fn
            return deco

    FastAPI = DummyApp  # type: ignore
try:
    from pydantic import BaseModel, Field
except Exception:  # minimal shim for environments without pydantic
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self):
            return {k: getattr(self, k) for k in self.__dict__.keys()}

    def Field(default=None, **_):  # type: ignore
        return default
from typing import List, Literal, Optional
import json
import os
from threading import RLock
from src.metrics import store as metrics_store
from src.metrics import decisions as decisions_store
from src.policy.engine import PolicyEngine as _PE, Rule as _PRule, Event as _PEvent
from scripts.setup_xevents import render_xevents_sql

app = FastAPI(title="SQLumAI Policy API", version="0.1.0")

RULES_PATH = os.getenv("RULES_PATH", "config/rules.json")
PROPOSED_RULES_PATH = os.getenv("PROPOSED_RULES_PATH", "config/rules_proposed.json")
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


@app.get("/metrics/prom")
def metrics_prom():
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        payload = generate_latest()  # includes our custom counters/histograms if imported
        return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
    except Exception:
        # Fallback to simple text exposition from JSON counters
        data = metrics_store.get_all()
        lines = [
            "# TYPE sqlumai_metric counter",
            "# HELP sqlumai_metric SQLumAI counters (by key)",
        ]
        for k, v in data.items():
            if k.startswith("rule:"):
                parts = k.split(":", 2)
                if len(parts) == 3:
                    _, rid, act = parts
                    lines.append(f'sqlumai_metric{{key="rule",rule="{rid}",action="{act}"}} {int(v)}')
                    continue
            lines.append(f'sqlumai_metric{{key="{k}"}} {int(v)}')
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")

@app.get("/insights.html")
def insights_html():
    # Render latest insights report if present
    import glob
    import html
    files = sorted(glob.glob("reports/insights-*.md"))
    if not files:
        return Response(content="<html><body><h1>No insights yet</h1></body></html>", media_type="text/html")
    text = open(files[-1], "r", encoding="utf-8").read()
    # naive markdown to HTML (headings + list)
    lines = []
    for ln in text.splitlines():
        if ln.startswith("# "):
            lines.append(f"<h1>{html.escape(ln[2:])}</h1>")
        elif ln.startswith("## "):
            lines.append(f"<h2>{html.escape(ln[3:])}</h2>")
        elif ln.startswith("- "):
            lines.append(f"<li>{html.escape(ln[2:])}</li>")
        else:
            lines.append(f"<p>{html.escape(ln)}</p>")
    body = "\n".join(lines)
    html_doc = f"<html><body>{body}<hr/><p><a href='/rules'>Rules</a></p></body></html>"
    return Response(content=html_doc, media_type="text/html")


@app.get("/dryrun.html")
def dryrun_html(rule: str | None = None, action: str | None = None, date: str | None = None):
    # Aggregate decisions by rule and action for today
    import datetime as dt
    day = (date or dt.datetime.now(dt.timezone.utc).date().isoformat())
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
    day = (date or dt.datetime.now(dt.timezone.utc).date().isoformat())
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


@app.get("/rules/ui")
def rules_ui():
    rules = _read_rules()
    rows = "".join(
        f"<tr><td>{r.id}</td><td>{r.target}</td><td>{r.selector}</td><td>{r.action}</td><td>{r.reason}</td></tr>"
        for r in rules
    )
    html = f"""
    <html><head><title>Rules UI</title><style>body{{font-family:Arial,sans-serif}} table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:4px}}</style></head>
    <body>
      <h1>Rules</h1>
      <table>
        <tr><th>Id</th><th>Target</th><th>Selector</th><th>Action</th><th>Reason</th></tr>
        {rows}
      </table>
      <h2>Add Rule</h2>
      <form id="f" onsubmit="ev(event)">
        <input name="id" placeholder="id"/> <select name="target"><option>table</option><option>column</option><option>pattern</option></select>
        <input name="selector" placeholder="selector"/> <select name="action"><option>allow</option><option>block</option><option>autocorrect</option></select>
        <input name="reason" placeholder="reason"/>
        <button type="submit">Create</button>
      </form>
      <script>
        async function ev(e){{e.preventDefault();const fd=new FormData(document.getElementById('f'));const body={{id:fd.get('id'),target:fd.get('target'),selector:fd.get('selector'),action:fd.get('action'),reason:fd.get('reason')}};await fetch('/rules',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});location.reload();}}
      </script>
      <h2>Test Decision</h2>
      <form id="t" onsubmit="tv(event)">
        <input name="table" placeholder="dbo.Table"/> <input name="column" placeholder="dbo.Table.Col"/> <input name="value" placeholder="value"/>
        <input name="sql_text" placeholder="optional SQL text" style="width:400px"/>
        <button type="submit">Preview</button>
      </form>
      <pre id="out"></pre>
      <script>
        async function tv(e){{e.preventDefault();const fd=new FormData(document.getElementById('t'));const body={{table:fd.get('table'),column:fd.get('column'),value:fd.get('value'),sql_text:fd.get('sql_text')}};const r=await fetch('/rules/test',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});document.getElementById('out').textContent=await r.text();}}
      </script>
    </body></html>
    """
    return html


class _TestEvent(BaseModel):
    table: Optional[str] = None
    column: Optional[str] = None
    value: Optional[str] = None
    sql_text: Optional[str] = None


@app.post("/rules/test")
def rules_test(ev: _TestEvent):
    rules = [_PRule(**r.model_dump()) for r in _read_rules()]
    pe = _PE(rules)
    dec = pe.decide(_PEvent(database=None, user=None, sql_text=ev.sql_text, table=ev.table, column=ev.column, value=ev.value))
    return dec.__dict__


def _read_rules_from(path: str) -> List[Rule]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [Rule(**r) for r in json.load(f)]


def _write_rules_to(path: str, rules: List[Rule]):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in rules], f, indent=2)


@app.get("/rules/proposed", response_model=List[Rule])
def list_rules_proposed():
    return _read_rules_from(PROPOSED_RULES_PATH)


@app.post("/rules/proposed", response_model=Rule)
def add_rule_proposed(rule: Rule):
    rules = _read_rules_from(PROPOSED_RULES_PATH)
    if any(r.id == rule.id for r in rules):
        raise HTTPException(status_code=409, detail="Rule id exists")
    rules.append(rule)
    _write_rules_to(PROPOSED_RULES_PATH, rules)
    return rule


@app.get("/rules/diff")
def rules_diff():
    cur = {r.id: r for r in _read_rules()}
    prop = {r.id: r for r in _read_rules_from(PROPOSED_RULES_PATH)}
    added = [r.model_dump() for k, r in prop.items() if k not in cur]
    removed = [r.model_dump() for k, r in cur.items() if k not in prop]
    changed = []
    for k in set(cur.keys()) & set(prop.keys()):
        if cur[k].model_dump() != prop[k].model_dump():
            changed.append({"id": k, "current": cur[k].model_dump(), "proposed": prop[k].model_dump()})
    return {"added": added, "removed": removed, "changed": changed}


@app.post("/rules/promote")
def rules_promote():
    proposed = _read_rules_from(PROPOSED_RULES_PATH)
    _write_rules(proposed)
    return {"promoted": len(proposed)}


@app.post("/xevents/setup")
def xevents_setup(mode: str = "ring"):
    mode = (mode or "ring").lower()
    if mode not in ("ring", "file"):
        raise HTTPException(status_code=400, detail="mode must be 'ring' or 'file'")
    sql = render_xevents_sql("file" if mode == "file" else "ring")
    return {"sql": sql}


class _SuggestReq(BaseModel):
    text: str


@app.post("/rules/suggest")
def rules_suggest(req: _SuggestReq):
    """
    Heuristic NL -> rule suggestion stub. Does not write rules.json.
    """
    t = req.text.lower()
    import re
    # Default suggestion
    suggestion = {
        "id": "suggest-1",
        "target": "pattern",
        "selector": "INSERT INTO",
        "action": "block",
        "reason": "Suggested from natural language",
        "confidence": 0.7,
        "enabled": True,
    }
    if any(k in t for k in ("phone", "telefon")):
        suggestion.update({
            "id": "phone-autocorrect",
            "target": "column",
            "selector": "Phone",
            "action": "autocorrect",
            "reason": "Normalize phone format",
            "confidence": 0.8,
        })
    if "email" in t and any(k in t for k in ("require", "krav", "måste", "must")):
        suggestion.update({
            "id": "no-null-email",
            "target": "column",
            "selector": "Email",
            "action": "block",
            "reason": "Email required",
            "confidence": 0.9,
        })
    # sanitize id
    suggestion["id"] = re.sub(r"[^a-z0-9\-]", "-", suggestion["id"])[:64]
    return suggestion
