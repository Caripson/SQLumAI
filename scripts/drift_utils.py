"""Compatibility shim for drift utilities.

This module re-exports functions from `scripts.archive.drift_utils` to maintain
backwards compatibility with tests and external scripts that import
`scripts.drift_utils`.
"""
from __future__ import annotations

try:
    # Preferred: archived location
    from .archive.drift_utils import compute_null_drift, null_ratio  # type: ignore
except Exception:  # pragma: no cover - fallback if archive not present
    from typing import Dict, Tuple, List

    def null_ratio(profile: Dict) -> float:
        cnt = max(1, int(profile.get("count", 0)))
        nulls = int(profile.get("nulls", 0))
        return nulls / cnt

    def compute_null_drift(
        prev: Dict[str, Dict], curr: Dict[str, Dict], threshold: float = 0.1
    ) -> List[Tuple[str, float]]:
        out: List[Tuple[str, float]] = []
        keys = set(prev.keys()) | set(curr.keys())
        for k in keys:
            p = prev.get(k, {})
            c = curr.get(k, {})
            d = abs(null_ratio(c) - null_ratio(p))
            if d >= threshold:
                out.append((k, d))
        out.sort(key=lambda kv: kv[1], reverse=True)
        return out

__all__ = ["compute_null_drift", "null_ratio"]

