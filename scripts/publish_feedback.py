#!/usr/bin/env python3
import os
import json
from pathlib import Path
import httpx

WEBHOOK = os.getenv("FEEDBACK_WEBHOOK", "")
LAST_REPORT = sorted(Path("reports").glob("report-*.md"))[-1] if Path("reports").exists() else None


def main():
    if not LAST_REPORT:
        raise SystemExit("No reports found.")
    content = LAST_REPORT.read_text()
    payload = {"text": content[:3000]}

    if WEBHOOK:
        try:
            r = httpx.post(WEBHOOK, json=payload, timeout=10)
            r.raise_for_status()
            print(f"Posted feedback to webhook: {WEBHOOK}")
        except Exception as e:
            print(f"Webhook post failed: {e}. Writing to local outbox.")
    outbox = Path("outbox")
    outbox.mkdir(exist_ok=True)
    out = outbox / f"feedback-{LAST_REPORT.stem}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote feedback payload to {out}")


if __name__ == "__main__":
    main()

