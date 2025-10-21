import fnmatch
import io
import os
import re
from pathlib import Path

BAD = re.compile(r"(^|\W)(from\s+dashboard\s+|import\s+dashboard\b|dashboard\.)")
EXCLUDES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "logs",
    "assets",
    "data",
    "build",
    "dist",
}


def _iter_py_files(root: Path, pattern: str = "*.py"):
    root = root.resolve()
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDES and not d.startswith(".")]
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                yield Path(base) / name


def test_no_legacy_imports():
    root = Path(__file__).resolve().parents[1]
    bad = []
    for path in _iter_py_files(root):
        sp = str(path).replace("\\", "/")
        if "/dashboard/" in sp and sp.endswith(".py"):
            # allow files within the legacy shim package itself
            continue
        try:
            with io.open(path, "r", encoding="utf-8", errors="ignore") as handle:
                txt = handle.read()
        except OSError:
            continue
        if BAD.search(txt):
            bad.append(sp)
    assert not bad, "Legacy 'dashboard' imports found:\n" + "\n".join(bad)
