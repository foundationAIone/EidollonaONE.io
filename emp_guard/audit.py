from __future__ import annotations

import json
import os
import time
from typing import Any

_LOG = os.path.join("logs", "emp_guard.ndjson")


def log(event: str, **payload: Any) -> None:
    """Append an NDJSON audit line; silently ignore filesystem errors."""
    try:
        os.makedirs("logs", exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"ts": time.time(), "event": event, **payload}) + "\n"
            )
    except Exception:
        # Defensive posture: never raise from audit helper
        pass
