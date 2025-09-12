import pathlib
import re

BAD = re.compile(r"(^|\W)(from\s+dashboard\s+|import\s+dashboard\b|dashboard\.)")


def test_no_legacy_imports():
    root = pathlib.Path(__file__).resolve().parents[1]
    bad = []
    for p in root.rglob("*.py"):
        sp = str(p).replace("\\", "/")
        if "/dashboard/" in sp and sp.endswith(".py"):
            # allow files within the legacy shim package itself
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if BAD.search(txt):
            bad.append(sp)
    assert not bad, "Legacy 'dashboard' imports found:\n" + "\n".join(bad)
