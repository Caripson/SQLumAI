#!/usr/bin/env python3
"""
Validates config/rules.json against the API schema (src.api.Rule).
Usage: python scripts/validate_rules.py [path/to/rules.json]
Exits with non-zero status if validation fails.
"""
import json
import sys
from pathlib import Path
from typing import Tuple


def main():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        path = Path("config/rules.json")
    if not path.exists():
        print(f"Rules file not found: {path}")
        sys.exit(1)

    # Ensure project root is importable
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Try to use Pydantic model if available; otherwise, use a lightweight validator
    Rule = None
    ValidationError = Exception  # type: ignore
    try:
        from src.api import Rule as _Rule  # pydantic model if installed
        Rule = _Rule
        try:
            from pydantic import ValidationError as _VE  # type: ignore
            ValidationError = _VE  # type: ignore
        except Exception:
            pass
    except Exception:
        Rule = None

    def _validate_rule(raw: dict) -> Tuple[bool, str | None]:
        # Minimal schema checks when Pydantic is unavailable
        allowed_targets = {"table", "column", "pattern"}
        allowed_actions = {"allow", "block", "autocorrect"}
        def err(msg: str) -> Tuple[bool, str]:
            return False, msg
        if not isinstance(raw, dict):
            return err("Rule must be an object")
        rid = raw.get("id")
        if not isinstance(rid, str) or not rid:
            return err("id must be a non-empty string")
        tgt = raw.get("target")
        if tgt not in allowed_targets:
            return err(f"target must be one of {sorted(allowed_targets)}")
        sel = raw.get("selector")
        if not isinstance(sel, str) or not sel:
            return err("selector must be a non-empty string")
        act = raw.get("action")
        if act not in allowed_actions:
            return err(f"action must be one of {sorted(allowed_actions)}")
        rsn = raw.get("reason", "")
        if rsn is not None and not isinstance(rsn, str):
            return err("reason must be a string if provided")
        conf = raw.get("confidence", 1.0)
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            return err("confidence must be a number between 0 and 1")
        en = raw.get("enabled", True)
        if not isinstance(en, bool):
            return err("enabled must be boolean if provided")
        envs = raw.get("apply_in_envs")
        if envs is not None:
            if not isinstance(envs, list) or not all(isinstance(x, str) for x in envs):
                return err("apply_in_envs must be a list of strings")
        mhte = raw.get("min_hits_to_enforce", 0)
        if not isinstance(mhte, int) or mhte < 0:
            return err("min_hits_to_enforce must be a non-negative integer")
        return True, None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read JSON: {e}")
        sys.exit(1)

    if not isinstance(data, list):
        print("Rules file must be a JSON list of rule objects")
        sys.exit(1)

    seen_ids = set()
    errors = 0
    for i, raw in enumerate(data):
        if Rule is not None:
            try:
                rule = Rule(**raw)  # type: ignore[misc]
                rid = getattr(rule, "id", None)
            except ValidationError as ve:  # type: ignore[name-defined]
                print(f"Rule[{i}] validation error: {ve}")
                errors += 1
                continue
        else:
            ok, msg = _validate_rule(raw)
            if not ok:
                print(f"Rule[{i}] validation error: {msg}")
                errors += 1
                continue
            rid = raw.get("id")
        if rid in seen_ids:
            print(f"Rule[{i}] duplicate id: {rid}")
            errors += 1
        seen_ids.add(rid)

    if errors:
        print(f"Validation FAILED with {errors} error(s)")
        sys.exit(2)
    print(f"Validation OK: {len(seen_ids)} rule(s)")


if __name__ == "__main__":
    main()
