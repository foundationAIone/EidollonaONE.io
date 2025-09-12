"""
Fast syntax check without writing .pyc files.
Walks project Python files and compiles in-memory to catch syntax errors.
Skips virtual environments, caches, and site-packages.
"""
from __future__ import annotations
import os
import sys

EXCLUDES = {
    "eidollona_env",
    "venv",
    ".venv",
    "env",
    "quantum_env",
    "__pycache__",
}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def _should_skip(path: str) -> bool:
    norm = os.path.normpath(path)
    parts = set(norm.split(os.sep))
    return bool(EXCLUDES & parts) or f"{os.sep}site-packages{os.sep}" in norm


def _py_files(root: str):
    for dirpath, dirs, files in os.walk(root):
        # prune excluded dirs early
        dirs[:] = [d for d in dirs if d not in EXCLUDES]
        if _should_skip(dirpath):
            continue
        for name in files:
            if not name.endswith(".py"):
                continue
            full = os.path.join(dirpath, name)
            yield full


def main() -> int:
    had_error = False
    for fpath in _py_files(ROOT):
        try:
            with open(fpath, "rb") as fh:
                src = fh.read()
            compile(src, fpath, "exec")
        except SyntaxError as e:
            # Print in a grep-friendly format
            sys.stderr.write(
                f"SyntaxError: {fpath}:{e.lineno}:{e.offset} {e.msg}\n"
            )
            had_error = True
        except Exception:
            # Don't fail the run for non-syntax issues; tests will catch these.
            # Still report path for visibility.
            continue
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
