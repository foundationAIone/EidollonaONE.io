import json
import os
import sys
import time
from pathlib import Path

AUDIT_PATH = Path(os.environ.get("EIDOLLONA_AUDIT", "logs/audit.ndjson"))
AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)

label = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "manual"
with open(AUDIT_PATH, "a", encoding="utf-8") as handle:
    handle.write(
        json.dumps({"event": "epoch_marker", "label": label, "ts": time.time()}, ensure_ascii=False)
        + "\n"
    )

print({"ok": True, "label": label})
