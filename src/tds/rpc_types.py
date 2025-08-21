import json
import os
from typing import Dict


def load_param_types(path: str | None = None) -> Dict[str, Dict[str, str]]:
    """
    Returns a mapping: { proc_name: { param_name: type } }
    param_name may include or exclude '@'; case-insensitive.
    """
    p = path or os.getenv("RPC_PARAM_TYPES_PATH", "config/rpc_param_types.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        out: Dict[str, Dict[str, str]] = {}
        for proc, mp in raw.items():
            out[proc.lower()] = { (k.lstrip("@").lower()): v for k, v in mp.items() }
        return out
    except Exception:
        return {}

