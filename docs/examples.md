# Examples

## Sample Events JSONL
- Path: `examples/events-sample.jsonl`
- Lines are JSON objects representing observed events. Minimal keys used by the simulator:
  - `sql_text` (string)
  - `table` (string, e.g., `dbo.Customers`)
  - `column` (string, e.g., `dbo.Customers.Email`)
  - `value` (string)

Run a dry‑run simulation against this file:
```bash
make simulate INPUT=examples/events-sample.jsonl
```

You can copy this file and tweak values to test rules, normalizers, and SELECT analysis.

