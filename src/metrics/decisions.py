import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

_path = os.getenv("DECISIONS_PATH", "data/metrics/decisions.jsonl")


def append(decision: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_path) or ".", exist_ok=True)
    d = {"ts": datetime.now(timezone.utc).isoformat(), **decision}
    with open(_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(d) + "\n")


def tail(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.exists(_path):
        return []
    lines: List[str] = []
    with open(_path, "r", encoding="utf-8") as f:
        for line in f:
            lines.append(line)
    out: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out

