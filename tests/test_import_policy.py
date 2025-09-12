"""Import Policy Guard Tests

Fails if deprecated / disallowed imports are reintroduced.
Deprecated namespaces:
  - rpm_ecosystem (root-level legacy)
  - ai_core.trading_bots (old alias)
"""

from __future__ import annotations
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

FORBIDDEN = [
    r"(^|\s|,)import\s+rpm_ecosystem",
    r"from\s+rpm_ecosystem\s+import",
    r"(^|\s|,)import\s+ai_core\.trading_bots",
    r"from\s+ai_core\.trading_bots\s+import",
]
REGEXES = [re.compile(p) for p in FORBIDDEN]

# Only scan explicit source directories to avoid huge env/site-packages trees
SCAN_DIRS = [
    "ai_core",
    "connection",
    "symbolic_core",
    "autonomous_governance",
    "master_key",
    "tools",
    "scripts",
]
EXCLUDE_NAMES = {
    ".git",
    "__pycache__",
    "eidollona_env",
    "quantum_env",
    "env",
    ".venv",
    "venv",
}

violations: list[str] = []
for d in SCAN_DIRS:
    base = ROOT / d
    if not base.exists():
        continue
    for py in base.rglob("*.py"):
        if any(part in EXCLUDE_NAMES for part in py.parts):
            continue
        try:
            txt = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(rx.search(txt) for rx in REGEXES):
            violations.append(str(py.relative_to(ROOT)))


def test_no_forbidden_imports():
    assert not violations, f"Forbidden legacy imports present: {violations}"
