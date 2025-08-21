import json
import os
from threading import RLock
from typing import Dict
try:
    from .prom_registry import inc_counter as prom_inc
except Exception:
    def prom_inc(key: str, rule: str | None = None, action: str | None = None, by: int = 1):
        return

_lock = RLock()
_path = os.getenv("METRICS_PATH", "data/metrics/metrics.json")


def _ensure_dir():
    d = os.path.dirname(_path) or "."
    os.makedirs(d, exist_ok=True)


def _read() -> Dict[str, int]:
    if not os.path.exists(_path):
        return {}
    try:
        with open(_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write(data: Dict[str, int]):
    _ensure_dir()
    with open(_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def inc(key: str, by: int = 1):
    with _lock:
        data = _read()
        data[key] = int(data.get(key, 0)) + by
        _write(data)
    try:
        prom_inc(key, None, None, by)
    except Exception:
        pass


def get_all() -> Dict[str, int]:
    with _lock:
        return _read()


def inc_rule_action(rule_id: str, action: str, by: int = 1):
    inc(f"rule:{rule_id}:{action}", by)
    try:
        prom_inc("rule", rule_id, action, by)
    except Exception:
        pass


def get_rule_counters(rule_id: str) -> Dict[str, int]:
    data = _read()
    out = {}
    prefix = f"rule:{rule_id}:"
    for k, v in data.items():
        if k.startswith(prefix):
            out[k[len(prefix):]] = v
    return out
