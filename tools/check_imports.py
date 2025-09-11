import pathlib
import re
import sys

# Limit directories to avoid traversing virtual environments
SCAN_DIRS = [
    "ai_core",
    "connection",
    "symbolic_core",
    "autonomous_governance",
    "master_key",
    "tools",
    "scripts",
]
FORBIDDEN_PATTERN = re.compile(r"\bai_core\.trading_bots\b")
legacy_hits = []
for d in SCAN_DIRS:
    base = pathlib.Path(d)
    if not base.exists():
        continue
    for p in base.rglob("*.py"):
        try:
            s = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if FORBIDDEN_PATTERN.search(s):
            legacy_hits.append(str(p))
if legacy_hits:
    print("Found legacy imports:", *[" - " + x for x in legacy_hits], sep="\n")
    sys.exit(1)
