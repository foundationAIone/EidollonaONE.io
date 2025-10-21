"""Derive minimal metrics from audit.ndjson."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict

AUDIT_PATH = Path("logs/audit.ndjson")


def rollup() -> Dict[str, int]:
    counter = Counter()
    if not AUDIT_PATH.exists():
        return {}
    with AUDIT_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
                counter[payload.get("event", "unknown")] += 1
            except json.JSONDecodeError:
                continue
    return dict(counter)


if __name__ == "__main__":
    print(json.dumps(rollup(), indent=2))
