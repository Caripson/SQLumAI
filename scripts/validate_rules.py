#!/usr/bin/env python3
"""
Validates config/rules.json against the API schema (src.api.Rule).
Usage: python scripts/validate_rules.py [path/to/rules.json]
Exits with non-zero status if validation fails.
"""
import json
import sys
from pathlib import Path


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

    try:
        from src.api import Rule  # pydantic model
        from pydantic import ValidationError  # type: ignore
    except Exception as e:
        print(f"Import error: {e}")
        sys.exit(1)

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
        try:
            rule = Rule(**raw)
        except ValidationError as ve:  # type: ignore[name-defined]
            print(f"Rule[{i}] validation error: {ve}")
            errors += 1
            continue
        if rule.id in seen_ids:
            print(f"Rule[{i}] duplicate id: {rule.id}")
            errors += 1
        seen_ids.add(rule.id)

    if errors:
        print(f"Validation FAILED with {errors} error(s)")
        sys.exit(2)
    print(f"Validation OK: {len(seen_ids)} rule(s)")


if __name__ == "__main__":
    main()

