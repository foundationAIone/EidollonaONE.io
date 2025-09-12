"""Guard script: enforce migration to SymbolicEquation41.

Scans the repository for legacy imports of SymbolicEquation / Reality from
symbolic_core.symbolic_equation that are not explicitly using SymbolicEquation41 or SE41Signals
and returns non-zero exit if any remain outside approved allowlists.

Usage (pre-commit / CI):
  python scripts/enforce_symbolic_v41.py --fail

Exit codes:
 0 = clean
 1 = legacy imports found
"""

from __future__ import annotations
import re
import pathlib
import argparse

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOW_DIRS = {
    "tests",  # tests may intentionally import legacy alias
    "MIGRATION_NOTES.md",
}
PATTERN = re.compile(r"from\s+symbolic_core\.symbolic_equation\s+import\s+([^\n]+)")

LEGACY_NAMES = {"SymbolicEquation", "Reality"}


def scan() -> list[tuple[pathlib.Path, str]]:
    offenders: list[tuple[pathlib.Path, str]] = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT)
        # skip virtual env or hidden
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts and rel.parts[0] in {"eidollona_env", "venv", "__pycache__"}:
            continue
        if rel.parts and rel.parts[0] in ALLOW_DIRS:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in PATTERN.finditer(text):
            imported = {x.strip() for x in m.group(1).split(",")}
            legacy_used = imported & LEGACY_NAMES
            if legacy_used and "SymbolicEquation41" not in imported:
                offenders.append((rel, ",".join(sorted(legacy_used))))
    return offenders


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail", action="store_true", help="Return non-zero on offenders")
    args = ap.parse_args(argv)
    offenders = scan()
    if offenders:
        print("Legacy symbolic imports detected:")
        for rel, names in offenders:
            print(f"  {rel} -> {names}")
    else:
        print("No legacy symbolic imports remaining (outside allowlist).")
    if offenders and args.fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
