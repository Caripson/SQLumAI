import json
import os
from typing import List
from .engine import Rule


def load_rules(path: str | None = None) -> List[Rule]:
    rules_path = path or os.getenv("RULES_PATH", "config/rules.json")
    if not os.path.exists(rules_path):
        return []
    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rules: List[Rule] = []
    for r in data:
        try:
            # Basic schema validation to align with API expectations
            tgt = (r.get("target") or "").lower()
            act = (r.get("action") or "").lower()
            sel = r.get("selector")
            if tgt not in ("table", "column", "pattern"):
                continue
            if act not in ("allow", "block", "autocorrect"):
                continue
            if not isinstance(sel, str):
                continue
            rules.append(Rule(**r))
        except Exception:
            continue
    return rules
