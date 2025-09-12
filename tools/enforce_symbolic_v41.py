"""Symbolic SE41 Enforcement Guard

Phase 1: Ensures evaluate(...) methods inside ai_core/ and symbolic_core/ follow
minimum SE41 v4.1 expectations:
  - Function name: evaluate
  - Accepts at least one parameter (ctx/context/input_data) suggesting context
  - Emits an ethos / alignment decision artifact name in source (ethos or alignment keyword)

Exit codes:
  0 = all good
  1 = violations found

This is a lightweight static scan (no AST heavy parse) to keep runtime fast.
"""

from __future__ import annotations
import sys
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET_DIRS = [ROOT / "ai_core", ROOT / "symbolic_core"]
EVAL_REGEX = re.compile(r"def\s+evaluate\s*\(([^)]*)\)")
ETHOS_HINTS = ("ethos", "alignment", "coherence")

violations = []

for base in TARGET_DIRS:
    if not base.exists():
        continue
    for path in base.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in EVAL_REGEX.finditer(text):
            params = m.group(1).strip()
            # Skip self/cls only definitions (need a context param)
            raw_params = [p.strip() for p in params.split(",") if p.strip()]
            has_context_like = any(
                any(k in p for k in ("ctx", "context", "input_data"))
                for p in raw_params
            )
            if not has_context_like:
                violations.append(f"{path}: evaluate() missing context-like parameter")
            # Must contain ethos/alignment hint somewhere in file near definition
            snippet_start = max(0, m.start() - 300)
            snippet_end = min(len(text), m.end() + 400)
            snippet = text[snippet_start:snippet_end].lower()
            if not any(h in snippet for h in ETHOS_HINTS):
                violations.append(
                    f"{path}: evaluate() missing ethos/alignment signal reference"
                )

if violations:
    print("SE41 Enforcement Violations:")
    for v in violations:
        print(" -", v)
    sys.exit(1)
else:
    print("SE41 enforcement passed: all evaluate() signatures/context look acceptable.")
    sys.exit(0)
